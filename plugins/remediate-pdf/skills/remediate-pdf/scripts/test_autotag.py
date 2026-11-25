#!/usr/bin/env python3
"""Unit + CLI error-path tests for autotag.py (no API key or network needed).

Pure-function tests cover input validation, anti-SSRF URL validation, the quota gate, key
redaction, and the build-stats quota note. CLI tests run the script via plain `python3` (error
paths exit before httpx/pypdf import) to confirm fail-fast behavior.

Run: `python3 test_autotag.py`
"""

import asyncio
import io
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx

sys.path.insert(0, str(Path(__file__).parent))
import autotag as A  # noqa: E402

SCRIPT = Path(__file__).parent / "autotag.py"
FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "sample.pdf"
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


# --- shared helpers: keys, addresses, output paths ------------------------------------------
def test_normalize_key_strips_and_rejects_bad_characters():
    assert A.normalize_key(" pdf_live_abc\r\n") == "pdf_live_abc"
    assert A.normalize_key("") is None and A.normalize_key("  ") is None
    assert A.normalize_key(None) is None
    for bad in ("pdf live", "pdf_live_\u00e4", "pdf_live\x00x"):
        try:
            A.normalize_key(bad)
            assert False, repr(bad)
        except ValueError as e:
            assert bad not in str(e)  # the error never echoes the key


def test_redact_handles_several_secrets():
    out = A.redact("key k1 and password p@ss", "k1", "p@ss", None)
    assert "k1" not in out and "p@ss" not in out


def test_is_public_ip_looks_inside_nat64_and_mapped():
    assert A.is_public_ip("93.184.216.34")
    assert not A.is_public_ip("10.0.0.1")
    assert not A.is_public_ip("64:ff9b::7f00:1")      # NAT64 of 127.0.0.1
    assert not A.is_public_ip("::ffff:192.168.1.1")    # IPv4-mapped private
    assert A.is_public_ip("64:ff9b::5db8:d822")        # NAT64 of a public address


def test_url_rejects_non_default_port():
    for bad in ("https://93.184.216.34:8443/x.pdf", "https://93.184.216.34:22/x.pdf"):
        try:
            A.validate_remote_url(bad)
            assert False, bad
        except ValueError as e:
            assert "443" in str(e)


def test_check_output_path_refuses_overwrite_input_and_existing():
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "doc.pdf"
        src.write_bytes(b"%PDF-1.4")
        for target, overwrite in ((src, True), (src, False)):
            try:
                A.check_output_path(target, src, overwrite)
                assert False
            except ValueError as e:
                assert "input" in str(e)
        existing = Path(d) / "out.pdf"
        existing.write_bytes(b"x")
        try:
            A.check_output_path(existing, src, False)
            assert False
        except ValueError as e:
            assert "--overwrite" in str(e)
        A.check_output_path(existing, src, True)            # allowed with --overwrite
        A.check_output_path(Path(d) / "new" / "o.pdf", src, False)  # creates the directory


def test_check_output_path_refuses_alias_of_input():
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "doc.pdf"
        src.write_bytes(b"%PDF-1.4")
        alias = Path(d) / "other-name.pdf"
        os.link(src, alias)
        try:
            A.check_output_path(alias, src, overwrite=True)
            assert False, "expected rejection for another name for the same input"
        except ValueError as e:
            assert "would overwrite the input" in str(e)


def test_write_private_resets_mode_and_refuses_existing():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "o.pdf"
        out.write_bytes(b"old")
        os.chmod(out, 0o644)
        try:
            A.write_private(out, b"new", overwrite=False)
            assert False, "expected FileExistsError"
        except FileExistsError:
            pass
        A.write_private(out, b"new", overwrite=True)
        assert out.read_bytes() == b"new"
        if os.name != "nt":
            assert (out.stat().st_mode & 0o777) == 0o600


def test_write_private_without_unix_only_file_apis():
    portable_os = SimpleNamespace(**{
        name: value for name, value in vars(os).items()
        if name not in {"O_NOFOLLOW", "fchmod"}
    })
    with tempfile.TemporaryDirectory() as d, patch.object(A, "os", portable_os):
        out = Path(d) / "output.pdf"
        A.write_private(out, b"first\r\n", overwrite=False)
        assert out.read_bytes() == b"first\r\n"
        A.write_private(out, b"second\r\n", overwrite=True)
        assert out.read_bytes() == b"second\r\n"


def test_write_private_preserves_existing_output_if_replace_fails():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "output.pdf"
        out.write_bytes(b"original")
        with patch.object(os, "replace", side_effect=PermissionError("destination is busy")):
            try:
                A.write_private(out, b"replacement", overwrite=True)
                assert False, "expected PermissionError"
            except PermissionError:
                pass
        assert out.read_bytes() == b"original"
        assert list(Path(d).iterdir()) == [out]


# --- CLI error paths (subprocess, plain python3) --------------------------------------------
def _run(args, env_extra=None):
    env = dict(os.environ)
    env.pop("NUTRIENT_ACCESSIBILITY_API_KEY", None)
    env.pop("NUTRIENT_API_KEY", None)
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


def test_key_with_inner_space_fails_without_echoing_it():
    r = _run(["--input", "x.pdf"], {"NUTRIENT_ACCESSIBILITY_API_KEY": "pdf_live secret"})
    assert r.returncode == 1 and "secret" not in r.stderr


def test_nutrient_api_key_fallback_is_accepted():
    r = _run(["--input", "/nope/missing.pdf"], {"NUTRIENT_API_KEY": "k"})
    assert r.returncode == 1 and "not found" in r.stderr


def test_scan_without_text_layer_exits_4():
    from pypdf import PdfWriter

    with tempfile.TemporaryDirectory() as d:
        scan = Path(d) / "scan.pdf"
        output = Path(d) / "new" / "tagged.pdf"
        for pages in (A.DEFAULT_CONFIRM_OVER + 1, 1):
            writer = PdfWriter()
            for _ in range(pages):
                writer.add_blank_page(612, 792)
            writer.write(scan)
            argv = ["autotag.py", "--input", str(scan), "--output", str(output)]
            stderr = io.StringIO()
            with (
                patch.dict(os.environ, {"NUTRIENT_ACCESSIBILITY_API_KEY": "review_dummy"}),
                patch.object(sys, "argv", argv),
                patch.object(sys.stdin, "isatty", return_value=False),
                patch.object(httpx, "AsyncClient", side_effect=AssertionError("unexpected HTTP client")),
                redirect_stderr(stderr),
            ):
                try:
                    asyncio.run(A.main())
                    assert False, "expected a CLI exit"
                except SystemExit as e:
                    assert e.code == 4 and "ocr.py" in stderr.getvalue()
            assert not output.parent.exists()


def test_pdf_with_text_after_blank_front_matter_does_not_require_ocr():
    from pypdf import PdfWriter

    with tempfile.TemporaryDirectory() as d:
        pdf = Path(d) / "late-text.pdf"
        writer = PdfWriter()
        for _ in range(3):
            writer.add_blank_page(612, 792)
        writer.append(FIXTURE)
        writer.write(pdf)
        assert A.has_text_layer(pdf) is True


def test_downloaded_scan_is_rejected_before_upload():
    from pypdf import PdfWriter

    scan = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(612, 792)
    writer.write(scan)
    url = "https://93.184.216.34/scan.pdf"
    fetch = AsyncMock(return_value=(scan.getvalue(), "scan.pdf"))
    with tempfile.TemporaryDirectory() as d:
        output = Path(d) / "tagged.pdf"
        argv = ["autotag.py", "--url", url, "--output", str(output), "--yes"]
        client = AsyncMock()
        with (
            patch.dict(os.environ, {"NUTRIENT_ACCESSIBILITY_API_KEY": "review_dummy"}),
            patch.object(sys, "argv", argv),
            patch.object(A, "fetch_remote_pdf", fetch),
            patch.object(httpx, "AsyncClient", return_value=client),
            redirect_stderr(io.StringIO()),
        ):
            try:
                asyncio.run(A.main())
                assert False, "expected a CLI exit"
            except SystemExit as e:
                assert e.code == 4
        fetch.assert_awaited_once()
        client.__aenter__.return_value.post.assert_not_awaited()
        assert not output.exists()


def test_existing_output_refused_before_any_call():
    try:
        from pypdf import PdfWriter  # noqa: F401
    except ImportError:
        print("SKIP test_existing_output_refused_before_any_call (pypdf not installed)")
        return
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "o.pdf"
        out.write_bytes(b"x")
        r = _run(["--input", str(FIXTURE), "--output", str(out), "--yes"],
                 {"NUTRIENT_ACCESSIBILITY_API_KEY": "k"})
        assert r.returncode == 1 and "--overwrite" in r.stderr


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
