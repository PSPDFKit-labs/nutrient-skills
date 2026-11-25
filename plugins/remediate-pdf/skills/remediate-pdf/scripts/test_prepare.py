#!/usr/bin/env python3
"""Unit + CLI error-path tests for prepare.py (no API key or network needed).

The /build instructions match requests run against the live Processor API: Word-to-PDF with
{"parts": [{"file": "document"}]}, and OCR with an added {"type": "ocr", "language": "english"}
action.

Run: `python3 test_prepare.py` (Python 3.10+)
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import prepare as P  # noqa: E402

SCRIPT = Path(__file__).parent / "prepare.py"
FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "sample.pdf"


def _tmp(suffix):
    f = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    f.write(b"x")
    f.close()
    return Path(f.name)


def test_classify_input():
    assert P.classify_input(_tmp(".docx")) == "office"
    assert P.classify_input(_tmp(".PPTX")) == "office"
    assert P.classify_input(_tmp(".txt")) == "office"
    assert P.classify_input(_tmp(".tiff")) == "image"
    assert P.classify_input(_tmp(".pdf")) == "pdf"


def test_classify_rejects_unsupported_and_missing():
    for suffix in (".csv", ".md", ".html"):
        try:
            P.classify_input(_tmp(suffix))
            assert False, f"{suffix} should be rejected"
        except ValueError as e:
            assert "unsupported" in str(e)
    try:
        P.classify_input(Path("/nope/missing.docx"))
        assert False
    except ValueError as e:
        assert "not found" in str(e)


def test_build_instructions():
    assert P.build_instructions(None) == {"parts": [{"file": "document"}]}
    assert P.build_instructions(["english"]) == {
        "parts": [{"file": "document"}],
        "actions": [{"type": "ocr", "language": "english"}],
    }
    multi = P.build_instructions(["english", "german"])
    assert multi["actions"][0]["language"] == ["english", "german"]


def test_parse_languages():
    assert P.parse_languages(None) is None
    assert P.parse_languages("english, german") == ["english", "german"]
    try:
        P.parse_languages(" , ")
        assert False
    except ValueError:
        pass


def test_default_output_never_overwrites_pdf_input():
    assert P.default_output(Path("/a/report.docx"), False) == Path("/a/report.pdf")
    assert P.default_output(Path("/a/scan.pdf"), True) == Path("/a/scan-ocr.pdf")


def test_text_layer_status_on_fixture():
    if not FIXTURE.is_file():
        print("SKIP test_text_layer_status_on_fixture (fixture missing)")
        return
    assert P.text_layer_status(FIXTURE) in (True, False)
    assert P.text_layer_status(Path("/nope/missing.pdf")) is None


# --- CLI error paths (exit before any network call) -----------------------------------------
def _run(args, env_extra=None):
    env = dict(os.environ)
    env.pop("NUTRIENT_ACCESSIBILITY_API_KEY", None)
    env.pop("NUTRIENT_API_KEY", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          env=env)


def test_help_exits_zero():
    r = _run(["--help"])
    assert r.returncode == 0 and "ocr" in r.stdout.lower()


def test_missing_key_fails_fast():
    r = _run(["--input", "x.docx"])
    assert r.returncode == 1 and "NUTRIENT_ACCESSIBILITY_API_KEY" in r.stderr


def test_unsupported_type_fails_fast():
    r = _run(["--input", str(_tmp(".csv"))], {"NUTRIENT_ACCESSIBILITY_API_KEY": "pdf_live_x"})
    assert r.returncode == 1 and "unsupported" in r.stderr


def test_pdf_without_ocr_is_a_no_op():
    r = _run(["--input", str(_tmp(".pdf"))], {"NUTRIENT_ACCESSIBILITY_API_KEY": "pdf_live_x"})
    assert r.returncode == 0 and "--ocr" in r.stderr


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
