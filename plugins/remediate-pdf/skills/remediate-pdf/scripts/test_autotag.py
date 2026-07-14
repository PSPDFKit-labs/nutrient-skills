#!/usr/bin/env python3
"""Unit + CLI error-path tests for autotag.py (no API key or network needed).

Pure-function tests cover input validation, anti-SSRF URL validation, the quota gate, key
redaction, and the build-stats quota note. CLI tests run the script via plain `python3` (error
paths exit before httpx/pypdf import) to confirm fail-fast behavior.

Run: `python3 test_autotag.py`
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import autotag as A  # noqa: E402

SCRIPT = Path(__file__).parent / "autotag.py"
REAL_BUILD_STATS = (
    '{"output":{"type":"pdfua","format":"pdf","page_count":1,"size_bytes":17728},'
    '"required_license_features":{"pdf_to_pdfua_api":{"units":1}}}'
)


# --- input validation (R6, R9) --------------------------------------------------------------
def test_validate_input_missing():
    try:
        A.validate_input(Path("/nope/missing.pdf"))
        assert False, "expected ValueError"
    except ValueError as e:
        assert "not found" in str(e)


def test_validate_input_non_pdf():
    with tempfile.NamedTemporaryFile(suffix=".txt") as f:
        try:
            A.validate_input(Path(f.name))
            assert False
        except ValueError as e:
            assert ".pdf" in str(e)


def test_validate_input_ok_and_oversize():
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(b"%PDF-1.4 hi")
        f.flush()
        A.validate_input(Path(f.name))            # ok
        orig = A.MAX_BYTES
        A.MAX_BYTES = 5
        try:
            A.validate_input(Path(f.name))
            assert False, "expected oversize ValueError"
        except ValueError as e:
            assert "limit" in str(e)
        finally:
            A.MAX_BYTES = orig


# --- anti-SSRF URL validation (R18) ---------------------------------------------------------
def test_url_requires_https():
    for bad in ["http://example.com/x.pdf", "ftp://example.com/x.pdf"]:
        try:
            A.validate_remote_url(bad)
            assert False, bad
        except ValueError as e:
            assert "https" in str(e)


def test_url_rejects_localhost_and_private():
    for bad in ["https://localhost/x.pdf", "https://127.0.0.1/x.pdf", "https://10.0.0.1/x.pdf"]:
        try:
            A.validate_remote_url(bad)
            assert False, bad
        except ValueError:
            pass


def test_url_accepts_public_ip_literal():
    A.validate_remote_url("https://8.8.8.8/x.pdf")  # public, should not raise


# --- quota gate (R16 / KD6) -----------------------------------------------------------------
def test_quota_gate():
    assert A.quota_gate(30, 20, yes=False, interactive=False)[0] is False
    assert A.quota_gate(30, 20, yes=True, interactive=False)[0] is True
    assert A.quota_gate(5, 20, yes=False, interactive=False)[0] is True
    assert A.quota_gate(30, 100, yes=False, interactive=False)[0] is True


def test_quota_gate_unknown_pages_requires_confirmation():
    # Unknown page count (remote --url / unreadable file) must NOT auto-proceed without --yes.
    blocked, msg = A.quota_gate(None, 20, yes=False, interactive=False)
    assert blocked is False and "unknown" in msg.lower()
    assert A.quota_gate(None, 20, yes=True, interactive=False)[0] is True


# --- redaction ------------------------------------------------------------------------------
def test_redact_removes_key():
    out = A.redact("oops key=pdf_live_secret in body", "pdf_live_secret")
    assert "pdf_live_secret" not in out and "[REDACTED]" in out


def test_is_pdf_response():
    assert A.is_pdf_response(b"%PDF-1.7\n...", "application/octet-stream")
    assert A.is_pdf_response(b"\x00\x00", "application/pdf; charset=binary")
    assert not A.is_pdf_response(b"<html>gateway</html>", "text/html")
    assert not A.is_pdf_response(b'{"error":"x"}', "application/json")


# --- quota note from build stats (R14 / OQ2) ------------------------------------------------
def test_quota_note_from_header():
    note = A.quota_note(REAL_BUILD_STATS, None)
    assert "1 page" in note and "1 quota unit" in note


def test_quota_note_fallback():
    assert "estimated" in A.quota_note(None, 7)
    assert "complete" in A.quota_note(None, None)


# --- CLI error paths (subprocess, plain python3) --------------------------------------------
def _run(args, env_extra=None):
    env = dict(os.environ)
    env.pop("NUTRIENT_ACCESSIBILITY_API_KEY", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, env=env)


def test_help_exits_zero():
    r = _run(["--help"])
    assert r.returncode == 0 and "auto-tag" in r.stdout.lower()


def test_missing_key_exits_nonzero():
    r = _run(["--input", "x.pdf"])
    assert r.returncode != 0 and "NUTRIENT_ACCESSIBILITY_API_KEY" in r.stderr


def test_empty_key_exits_nonzero():
    # An empty key must fail fast like a missing one (else it sends "Authorization: Bearer ").
    r = _run(["--input", "x.pdf"], env_extra={"NUTRIENT_ACCESSIBILITY_API_KEY": ""})
    assert r.returncode != 0 and "NUTRIENT_ACCESSIBILITY_API_KEY" in r.stderr


def test_missing_file_exits_nonzero():
    r = _run(["--input", "/nope/missing.pdf"], {"NUTRIENT_ACCESSIBILITY_API_KEY": "k"})
    assert r.returncode != 0 and "not found" in r.stderr


def test_non_pdf_exits_nonzero():
    with tempfile.NamedTemporaryFile(suffix=".txt") as f:
        r = _run(["--input", f.name], {"NUTRIENT_ACCESSIBILITY_API_KEY": "k"})
        assert r.returncode != 0 and ".pdf" in r.stderr


def test_url_http_rejected():
    r = _run(["--url", "http://example.com/x.pdf"], {"NUTRIENT_ACCESSIBILITY_API_KEY": "k"})
    assert r.returncode != 0 and "https" in r.stderr


def test_input_and_url_mutually_exclusive():
    r = _run(["--input", "a.pdf", "--url", "https://x/y.pdf"],
             {"NUTRIENT_ACCESSIBILITY_API_KEY": "k"})
    assert r.returncode != 0  # argparse rejects


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
