#!/usr/bin/env python3
"""Unit + CLI error-path tests for validate.py (no API key or network needed).

PASSING_REPORT and FAILING_REPORT are real /accessibility/validate_pdfua responses captured from
the live API (FAILING_REPORT is tests/fixtures/validation-failing.json, the untagged sample.pdf).

Run: `python3 test_validate.py` (Python 3.10+)
"""

import asyncio
import io
import json
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).parent))
import validate as V  # noqa: E402

SCRIPT = Path(__file__).parent / "validate.py"

PASSING_REPORT = {
    "conformance": "pdfua-1",
    "isValid": True,
    "validationReport": {
        "failedChecks": [],
        "failureCount": 0,
        "profile": {"conformance": "pdfua", "part": 1},
        "result": {
            "isCompliant": True,
            "statement": "PDF file is compliant with validation profile requirements.",
        },
    },
}

# A real failing response: the untagged tests/fixtures/sample.pdf, validated on 2026-11-25.
FAILING_REPORT = json.loads(
    (Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "validation-failing.json").read_text()
)


def test_conformant_only_when_isvalid_true():
    assert V.is_conformant(PASSING_REPORT) is True
    assert V.is_conformant(FAILING_REPORT) is False
    assert V.is_conformant({}) is False  # missing field never reads as a pass
    assert V.is_conformant({"isValid": "true"}) is False  # only a real boolean counts


def test_summary_pass():
    s = V.summarize_report(PASSING_REPORT, "doc.pdf")
    assert "passed PDF/UA-1 machine validation" in s and "no failed checks" in s
    assert "A person still needs to check" in s


def test_summary_fail_lists_checks_and_counts():
    s = V.summarize_report(FAILING_REPORT, "doc.pdf")
    assert "failed PDF/UA-1 validation" in s
    assert "8 failure(s) across 7 check(s)" in s
    assert "The font is not embedded. (2 occurrence(s), check UnembeddedFont)" in s
    assert "check MissingDocumentTitle" in s
    assert "3 0 obj" in s                       # a real object reference is shown
    assert "at None" not in s and "at 0 obj" not in s  # placeholders fall back to the context
    assert "at Document" in s


def test_summary_caps_listed_occurrences():
    report = {"isValid": False, "validationReport": {"failedChecks": [{
        "id": "x", "occurrenceCount": 5,
        "occurrences": [{"objectReference": f"{i} 0 R", "statement": "s"} for i in range(5)],
    }]}}
    s = V.summarize_report(report, "doc.pdf")
    assert "and 2 more" in s
    assert "4 0 R" not in s


def test_summary_counts_when_failurecount_missing():
    report = {"isValid": False, "validationReport": {"failedChecks": [
        {"id": "a", "occurrenceCount": 2, "occurrences": []},
        {"id": "b", "occurrenceCount": 1, "occurrences": []},
    ]}}
    assert "3 failure(s) across 2 check(s)" in V.summarize_report(report, "doc.pdf")


def test_password_header_always_base64():
    import base64

    for pw in ("s3cret!", "pässwörd", "hunter2 ", " lead", "base64:literal"):
        value = V.password_header_value(pw)
        assert value.startswith("base64:") and pw not in value
        assert base64.b64decode(value[len("base64:"):]).decode("utf-8") == pw


def test_error_hints():
    assert "password is incorrect" in V.error_hint(403, sent_password=True)
    assert "NUTRIENT_PDF_PASSWORD" in V.error_hint(403, sent_password=False)
    assert "separate keys" in V.error_hint(401, False)
    assert "wallet" in V.error_hint(402, False)


# --- CLI error paths (exit before any network call) -----------------------------------------
def _run(args, env_extra=None):
    env = dict(os.environ)
    env.pop("NUTRIENT_ACCESSIBILITY_API_KEY", None)
    env.pop("NUTRIENT_API_KEY", None)
    env.pop("NUTRIENT_PDF_PASSWORD", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          env=env)


def test_help_exits_zero():
    r = _run(["--help"])
    assert r.returncode == 0 and "pdf/ua-1" in r.stdout.lower()


def test_missing_key_fails_fast():
    r = _run(["--input", "x.pdf"])
    assert r.returncode == 1 and "NUTRIENT_ACCESSIBILITY_API_KEY" in r.stderr


def test_missing_input_fails_fast():
    r = _run(["--input", "/nope/missing.pdf"], {"NUTRIENT_ACCESSIBILITY_API_KEY": "pdf_live_x"})
    assert r.returncode == 1 and "not found" in r.stderr


def test_url_requires_https():
    r = _run(["--url", "http://example.com/a.pdf"], {"NUTRIENT_ACCESSIBILITY_API_KEY": "pdf_live_x"})
    assert r.returncode == 1 and "https" in r.stderr


def test_missing_password_env_fails_fast():
    with tempfile.TemporaryDirectory() as d:
        pdf = Path(d) / "doc.pdf"
        pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
        r = _run(["--input", str(pdf), "--with-password"],
                 {"NUTRIENT_ACCESSIBILITY_API_KEY": "pdf_live_x"})
        assert r.returncode == 1 and "NUTRIENT_PDF_PASSWORD" in r.stderr


def test_report_cannot_overwrite_input_or_existing_file():
    with tempfile.TemporaryDirectory() as d:
        pdf = Path(d) / "doc.pdf"
        pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
        r = _run(["--input", str(pdf), "--report", str(pdf), "--overwrite"],
                 {"NUTRIENT_ACCESSIBILITY_API_KEY": "pdf_live_x"})
        assert r.returncode == 1 and "input" in r.stderr
        existing = Path(d) / "doc-validation.json"
        existing.write_text("{}")
        r = _run(["--input", str(pdf)], {"NUTRIENT_ACCESSIBILITY_API_KEY": "pdf_live_x"})
        assert r.returncode == 1 and "--overwrite" in r.stderr


def _run_with_response(input_file, output_file, response):
    """Run the CLI body with an HTTP 200 from a transport that never opens a socket."""
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=response)

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    stdout, stderr = io.StringIO(), io.StringIO()
    argv = ["validate.py", "--input", str(input_file), "--report", str(output_file)]
    with (
        patch.dict(os.environ, {"NUTRIENT_ACCESSIBILITY_API_KEY": "review_dummy"}),
        patch.object(sys, "argv", argv),
        patch.object(httpx, "AsyncClient", return_value=client),
        redirect_stdout(stdout),
        redirect_stderr(stderr),
    ):
        try:
            asyncio.run(V.main())
            assert False, "expected a CLI exit"
        except SystemExit as exit_result:
            assert len(requests) == 1
            assert requests[0].method == "POST" and str(requests[0].url) == V.VALIDATE_URL
            return exit_result.code, stdout.getvalue(), stderr.getvalue()


def test_completed_validations_write_report_and_use_distinct_verdicts():
    fixture = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "sample.pdf"
    with tempfile.TemporaryDirectory() as d:
        for response, expected_code, verdict in (
            (PASSING_REPORT, 0, "passed PDF/UA-1 machine validation"),
            (FAILING_REPORT, 3, "failed PDF/UA-1 validation"),
        ):
            dest = Path(d) / f"report-{expected_code}.json"
            code, stdout, stderr = _run_with_response(fixture, dest, response)
            assert code == expected_code and verdict in stdout and not stderr
            assert json.loads(dest.read_text(encoding="utf-8")) == response


def test_malformed_validation_response_is_an_error_without_a_verdict_or_report():
    fixture = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "sample.pdf"
    with tempfile.TemporaryDirectory() as d:
        for response in (
            [],
            {},
            {"isValid": True},
            {"isValid": False, "validationReport": {}},
            {"isValid": False, "validationReport": {"failedChecks": []}},
            {"isValid": True, "validationReport": {"failedChecks": [{"id": "MissingTitle"}]}},
        ):
            dest = Path(d) / "report.json"
            code, stdout, stderr = _run_with_response(fixture, dest, response)
            assert code == 1 and "validation report" in stderr
            assert not stdout and not dest.exists()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
