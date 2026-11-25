#!/usr/bin/env python3
"""Unit + CLI error-path tests for validate.py (no API key or network needed).

PASSING_REPORT is a real /accessibility/validate_pdfua response captured from the live API.
FAILING_REPORT follows the documented report schema (failedChecks entries with id,
occurrenceCount, and occurrences carrying context, objectReference, and statement); replace it with
a captured failing response when one is available.

Run: `python3 test_validate.py` (Python 3.10+)
"""

import os
import subprocess
import sys
from pathlib import Path

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

FAILING_REPORT = {
    "conformance": "none",
    "isValid": False,
    "validationReport": {
        "failureCount": 4,
        "profile": {"conformance": "pdfua", "part": 1},
        "result": {
            "isCompliant": False,
            "statement": "PDF file is not compliant with validation profile requirements.",
        },
        "failedChecks": [
            {
                "id": "7.18.1-2",
                "occurrenceCount": 3,
                "occurrences": [
                    {"context": "root/document[0]/pages[0]/annots[0]", "objectReference": "12 0 R",
                     "statement": "An annotation has no description."},
                    {"context": "root/document[0]/pages[0]/annots[1]", "objectReference": "13 0 R",
                     "statement": "An annotation has no description."},
                    {"context": "root/document[0]/pages[0]/annots[2]", "objectReference": "14 0 R",
                     "statement": "An annotation has no description."},
                ],
            },
            {
                "id": "7.1-8",
                "occurrenceCount": 1,
                "occurrences": [
                    {"context": "root/document[0]/metadata[0]", "objectReference": "1 0 R",
                     "statement": "The document has no title in its metadata."},
                ],
            },
        ],
    },
}


def test_conformant_only_when_isvalid_true():
    assert V.is_conformant(PASSING_REPORT) is True
    assert V.is_conformant(FAILING_REPORT) is False
    assert V.is_conformant({}) is False  # missing field never reads as a pass
    assert V.is_conformant({"isValid": "true"}) is False  # only a real boolean counts


def test_summary_pass():
    s = V.summarize_report(PASSING_REPORT, "doc.pdf")
    assert "conforms to PDF/UA-1" in s and "No failed checks" in s


def test_summary_fail_lists_checks_and_counts():
    s = V.summarize_report(FAILING_REPORT, "doc.pdf")
    assert "does not conform" in s
    assert "4 failure(s) across 2 check(s)" in s
    assert "An annotation has no description. (3 occurrence(s), check 7.18.1-2)" in s
    assert "The document has no title in its metadata." in s
    assert "12 0 R" in s


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


def test_password_header_ascii_and_base64():
    assert V.password_header_value("s3cret!") == "s3cret!"
    encoded = V.password_header_value("pässwörd")
    assert encoded.startswith("base64:") and "ä" not in encoded


# --- CLI error paths (exit before any network call) -----------------------------------------
def _run(args, env_extra=None):
    env = dict(os.environ)
    env.pop("NUTRIENT_ACCESSIBILITY_API_KEY", None)
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


def test_missing_password_env_fails_fast(tmp=Path("/tmp/validate-test.pdf")):
    tmp.write_bytes(b"%PDF-1.4\n%%EOF\n")
    r = _run(["--input", str(tmp), "--password-env", "NO_SUCH_VAR_XYZ"],
             {"NUTRIENT_ACCESSIBILITY_API_KEY": "pdf_live_x"})
    assert r.returncode == 1 and "NO_SUCH_VAR_XYZ" in r.stderr


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
