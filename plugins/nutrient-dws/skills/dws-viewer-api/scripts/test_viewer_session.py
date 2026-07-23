#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27", "pytest>=8.0"]
# ///
"""Keyless / mocked tests for viewer-session.py (plan U2 scenarios 1-3, 8-11).

Pure-function and mocked-API tests need no live key. Mocked tests use httpx.MockTransport so
no network is touched. Live scenarios (4-7) are the U5 smoke guide, not here.

Run: `uv run scripts/test_viewer_session.py`  (or `pytest`)
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import importlib.util

import httpx
import pytest

SCRIPT = Path(__file__).parent / "viewer-session.py"

# The script is hyphenated (not importable by name) — load it from its path.
_spec = importlib.util.spec_from_file_location("viewer_session", SCRIPT)
vs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vs)


# --- pure helpers ---------------------------------------------------------------------------
def test_permissions_default_is_read_only():
    # Scenario 8 (least privilege, R-15): omitting flags yields exactly ["read"].
    assert vs.resolve_permissions(False, False, None) == ["read"]


def test_permissions_opt_in_write_download():
    # Scenario 9 (R-15 opt-in): flags add write and download.
    perms = vs.resolve_permissions(True, True, None)
    assert "write" in perms and "download" in perms and "read" in perms


def test_permissions_explicit_list_wins():
    assert vs.resolve_permissions(True, True, "read") == ["read"]
    assert vs.resolve_permissions(False, False, "read,write") == ["read", "write"]


def test_permissions_empty_explicit_falls_back_to_read():
    assert vs.resolve_permissions(False, False, " , ") == ["read"]


def test_clamp_expires_in_under_limit_no_warn():
    val, warn = vs.clamp_expires_in(3600)
    assert val == 3600 and warn is None


def test_clamp_expires_in_over_hour_warns():
    val, warn = vs.clamp_expires_in(2 * 3600)
    assert val == 2 * 3600 and warn is not None


def test_clamp_expires_in_over_ceiling_clamps():
    val, warn = vs.clamp_expires_in(48 * 3600)
    assert val == vs.MAX_EXPIRES_IN and "clamp" in warn.lower()


def test_build_session_body_managed():
    body = vs.build_session_body("DOC1", ["read"], 600)
    assert body["allowed_documents"][0]["document_id"] == "DOC1"
    assert body["allowed_documents"][0]["permissions"] == ["read"]
    assert isinstance(body["exp"], int)


def test_build_session_body_app_provided_is_empty():
    assert vs.build_session_body(None, [], 600) == {}


def test_redact_removes_key():
    assert "[REDACTED]" in vs.redact("oops pdf_live_secret leaked", "pdf_live_secret")
    assert vs.redact("clean", "pdf_live_secret") == "clean"


# --- mocked-API tests (httpx.MockTransport, no network, no key) ------------------------------
class _Args:
    def __init__(self, **kw):
        self.allow_write = kw.get("allow_write", False)
        self.allow_download = kw.get("allow_download", False)
        self.permissions = kw.get("permissions")
        self.expires_in = kw.get("expires_in", vs.DEFAULT_EXPIRES_IN)
        self.jwt_out = kw.get("jwt_out")
        self.document_id = kw.get("document_id")
        self.app_provided = kw.get("app_provided", False)
        self.file = kw.get("file")


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_session_default_body_is_read_only(capsys):
    # Scenario 8: mocked session mint — request body permissions == exactly ["read"].
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json={"jwt": "a.b.c"})

    with _client(handler) as c:
        vs.cmd_session(c, "KEY", _Args(document_id="DOC1"))
    perms = captured["body"]["allowed_documents"][0]["permissions"]
    assert perms == ["read"], f"expected least-privilege default, got {perms}"
    assert "jwt=a.b.c" in capsys.readouterr().out


def test_session_opt_in_body_has_write_download(capsys):
    # Scenario 9: --allow-write --allow-download reflected in request body.
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json={"jwt": "a.b.c"})

    with _client(handler) as c:
        vs.cmd_session(c, "KEY", _Args(document_id="DOC1", allow_write=True, allow_download=True))
    perms = captured["body"]["allowed_documents"][0]["permissions"]
    assert "write" in perms and "download" in perms


def test_app_provided_body_is_empty(capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content) == {}
        return httpx.Response(201, json={"jwt": "a.b.c"})

    with _client(handler) as c:
        vs.cmd_session(c, "KEY", _Args(app_provided=True))
    out = capsys.readouterr()
    assert "jwt=a.b.c" in out.out
    assert "app-provided" in out.err.lower()  # scope warning emitted to stderr


def test_jwt_only_to_stdout_never_stderr(capsys):
    # Scenario 10: the JWT is printed once to stdout and never appears in stderr.
    jwt = "header.payload.signature"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={"jwt": jwt})

    with _client(handler) as c:
        vs.cmd_session(c, "SECRETKEY", _Args(document_id="DOC1"))
    out = capsys.readouterr()
    assert out.out.count(jwt) == 1, "JWT must print exactly once"
    assert jwt not in out.err, "JWT must not leak to stderr"
    assert "SECRETKEY" not in out.out and "SECRETKEY" not in out.err, "API key must never appear"


def test_jwt_out_writes_0600_file(tmp_path, capsys):
    jwt = "a.b.c"
    dest = tmp_path / "jwt.txt"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={"jwt": jwt})

    with _client(handler) as c:
        vs.cmd_session(c, "KEY", _Args(document_id="DOC1", jwt_out=str(dest)))
    assert dest.read_text() == jwt
    assert (dest.stat().st_mode & 0o777) == 0o600
    out = capsys.readouterr()
    assert jwt not in out.out, "with --jwt-out the JWT must not also hit stdout"


def test_partial_failure_invokes_cleanup(tmp_path, capsys):
    # Scenario 11 (R-16): upload ok, session fails -> delete of the uploaded doc is invoked.
    calls = []
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4 minimal")

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.method == "POST" and request.url.path == "/viewer/documents":
            return httpx.Response(200, json={"data": {"document_id": "DOC1"}})
        if request.method == "POST" and request.url.path == "/viewer/sessions":
            return httpx.Response(500, text="boom")
        if request.method == "DELETE":
            return httpx.Response(200, text="OK")
        return httpx.Response(404)

    with _client(handler) as c:
        with pytest.raises(SystemExit) as e:
            vs.cmd_upload_and_session(c, "KEY", _Args(file=str(f)))
    assert e.value.code == 1
    assert ("DELETE", "/viewer/documents/DOC1") in calls, "cleanup delete was not invoked"
    err = capsys.readouterr().err
    assert "Cleaned up" in err


def _upload_then_session(session_response, delete_response=httpx.Response(200, text="OK")):
    """Build a MockTransport handler: upload -> DOC1, session -> session_response, delete -> given."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.method == "POST" and request.url.path == "/viewer/documents":
            return httpx.Response(200, json={"data": {"document_id": "DOC1"}})
        if request.method == "POST" and request.url.path == "/viewer/sessions":
            return session_response
        if request.method == "DELETE":
            return delete_response
        return httpx.Response(404)

    return handler, calls


def test_partial_failure_cleanup_also_fails_warns(tmp_path, capsys):
    # D: session fails AND delete fails -> a manual-cleanup WARNING naming the doc, not "Cleaned up".
    f = tmp_path / "doc.pdf"; f.write_bytes(b"%PDF-1.4")
    handler, _ = _upload_then_session(httpx.Response(500, text="boom"),
                                      delete_response=httpx.Response(500, text="nope"))
    with _client(handler) as c, pytest.raises(SystemExit) as e:
        vs.cmd_upload_and_session(c, "KEY", _Args(file=str(f)))
    assert e.value.code == 1
    err = capsys.readouterr().err
    assert "WARNING" in err and "DOC1" in err and "manually" in err
    assert "Cleaned up" not in err


def test_session_2xx_non_json_body_cleans_up(tmp_path, capsys):
    # B: a 2xx session response with a non-JSON body must NOT raise uncaught; it cleans up the doc.
    f = tmp_path / "doc.pdf"; f.write_bytes(b"%PDF-1.4")
    handler, calls = _upload_then_session(httpx.Response(200, text="<html>gateway</html>"))
    with _client(handler) as c, pytest.raises(SystemExit) as e:
        vs.cmd_upload_and_session(c, "KEY", _Args(file=str(f)))
    assert e.value.code == 1
    assert ("DELETE", "/viewer/documents/DOC1") in calls, "non-JSON 2xx must trigger cleanup"
    assert "no usable jwt" in capsys.readouterr().err


def test_session_2xx_missing_jwt_cleans_up(tmp_path, capsys):
    # D: a 2xx session response lacking the jwt key cleans up and reports.
    f = tmp_path / "doc.pdf"; f.write_bytes(b"%PDF-1.4")
    handler, calls = _upload_then_session(httpx.Response(200, json={"other": "field"}))
    with _client(handler) as c, pytest.raises(SystemExit) as e:
        vs.cmd_upload_and_session(c, "KEY", _Args(file=str(f)))
    assert e.value.code == 1
    assert ("DELETE", "/viewer/documents/DOC1") in calls
    assert "Cleaned up" in capsys.readouterr().err


def test_upload_missing_document_id_exits(capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {}})  # 2xx but no document_id

    with _client(handler) as c, pytest.raises(SystemExit) as e:
        vs.do_upload(c, "KEY", Path("/dev/null"))
    assert e.value.code == 1
    assert "no document_id" in capsys.readouterr().err


def test_session_missing_jwt_exits(capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={})  # 2xx but no jwt

    with _client(handler) as c, pytest.raises(SystemExit) as e:
        vs.cmd_session(c, "KEY", _Args(document_id="DOC1"))
    assert e.value.code == 1
    assert "no usable jwt" in capsys.readouterr().err


def test_fail_http_redacts_key(capsys):
    # The API key must be scrubbed from an HTTP error body (end-to-end through _fail_http).
    key = "pdf_live_SUPERSECRET"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text=f"unauthorized for key {key}")

    with _client(handler) as c, pytest.raises(SystemExit):
        vs.cmd_session(c, key, _Args(document_id="DOC1"))
    err = capsys.readouterr().err
    assert key not in err, "API key leaked into HTTP error output"
    assert "[REDACTED]" in err


def test_negative_expires_in_floors_to_default():
    # F: a non-positive TTL is floored to the default rather than minting an expired session.
    val, warn = vs.clamp_expires_in(-3600)
    assert val == vs.DEFAULT_EXPIRES_IN and warn is not None
    val0, warn0 = vs.clamp_expires_in(0)
    assert val0 == vs.DEFAULT_EXPIRES_IN and warn0 is not None


def test_jwt_out_overwrites_existing_and_enforces_0600(tmp_path, capsys):
    # A: an existing wider-mode file is overwritten and tightened to 0600 (path reuse works).
    dest = tmp_path / "jwt.txt"
    dest.write_text("stale"); os.chmod(dest, 0o644)
    vs.emit_jwt("a.b.c", str(dest))
    assert dest.read_text() == "a.b.c"
    assert (dest.stat().st_mode & 0o777) == 0o600


def test_jwt_out_refuses_symlink(tmp_path):
    # A: O_NOFOLLOW rejects a pre-planted symlink target (anti-redirect).
    target = tmp_path / "real.txt"; target.write_text("orig")
    link = tmp_path / "link.txt"; link.symlink_to(target)
    with pytest.raises(OSError):
        vs.emit_jwt("a.b.c", str(link))
    assert target.read_text() == "orig", "symlink target must be untouched"


def test_jwt_out_bad_dir_fails_before_upload(tmp_path, capsys):
    # C: a --jwt-out path in a missing directory fails fast, before any upload, so no orphan.
    f = tmp_path / "doc.pdf"; f.write_bytes(b"%PDF-1.4")
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        return httpx.Response(200, json={"data": {"document_id": "DOC1"}})

    bad = tmp_path / "no_such_dir" / "out.jwt"
    with _client(handler) as c, pytest.raises(SystemExit) as e:
        vs.cmd_upload_and_session(c, "KEY", _Args(file=str(f), jwt_out=str(bad)))
    assert e.value.code == 1
    assert calls == [], "no network call should happen when --jwt-out dir is invalid"
    assert "--jwt-out directory does not exist" in capsys.readouterr().err


def test_validate_jwt_out_rejects_symlink_and_dir(tmp_path):
    # Preflight rejects a symlink target and a directory target before any billable call.
    target = tmp_path / "real.txt"; target.write_text("x")
    link = tmp_path / "link.txt"; link.symlink_to(target)
    with pytest.raises(SystemExit):
        vs.validate_jwt_out(str(link))
    d = tmp_path / "adir"; d.mkdir()
    with pytest.raises(SystemExit):
        vs.validate_jwt_out(str(d))
    vs.validate_jwt_out(str(tmp_path / "ok.jwt"))  # a plain path in an existing dir is fine


def test_delete_subcommand_success_and_failure(capsys):
    # J: the delete subcommand surfaces do_delete with parseable output / non-zero on failure.
    def ok(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="OK")

    with _client(ok) as c:
        vs.cmd_delete(c, "KEY", _Args(document_id="DOC1"))
    assert "deleted=DOC1" in capsys.readouterr().out

    def gone(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Document not found")

    with _client(gone) as c, pytest.raises(SystemExit) as e:
        vs.cmd_delete(c, "KEY", _Args(document_id="DOC1"))
    assert e.value.code == 1


def test_transport_error_on_session_cleans_up(tmp_path, capsys):
    # R-16 gap: the session POST raises (timeout / DNS / TLS) before any response. The uploaded
    # document must still be torn down — a received-error-only cleanup would orphan it.
    calls = []
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4 minimal")

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.method == "POST" and request.url.path == "/viewer/documents":
            return httpx.Response(200, json={"data": {"document_id": "DOC1"}})
        if request.method == "POST" and request.url.path == "/viewer/sessions":
            raise httpx.ConnectTimeout("simulated network failure")
        if request.method == "DELETE":
            return httpx.Response(200, text="OK")
        return httpx.Response(404)

    with _client(handler) as c, pytest.raises(SystemExit) as e:
        vs.cmd_upload_and_session(c, "KEY", _Args(file=str(f)))
    assert e.value.code == 1
    assert ("DELETE", "/viewer/documents/DOC1") in calls, "transport error orphaned the upload"
    assert "Cleaned up" in capsys.readouterr().err


def test_delete_encodes_document_id_as_single_segment():
    # A document_id carrying '/' or '..' must be percent-encoded into one path segment so httpx
    # can't normalize it into a different endpoint.
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["raw"] = request.url.raw_path.decode()
        return httpx.Response(200, text="OK")

    with _client(handler) as c:
        assert vs.do_delete(c, "KEY", "a/b/../c") is True
    assert "a%2Fb%2F..%2Fc" in captured["raw"], captured["raw"]
    assert "/viewer/documents/a/" not in captured["raw"], "path separator leaked from document_id"


# --- CLI subprocess tests -------------------------------------------------------------------
def test_help_lists_subcommands():
    # Scenario 1: --help exits 0 and lists all subcommands (argparse runs before httpx import).
    r = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True)
    assert r.returncode == 0
    for cmd in ("upload", "session", "upload-and-session", "delete"):
        assert cmd in r.stdout


def test_missing_key_fails_fast():
    # Scenario 2: empty key -> exit 1, message names the env var (require_key before httpx import).
    env = {**os.environ, "NUTRIENT_DWS_VIEWER_API_KEY": ""}
    env.pop("NUTRIENT_API_KEY", None)
    r = subprocess.run([sys.executable, str(SCRIPT), "upload", "--file", "x.pdf"],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 1
    assert "NUTRIENT_DWS_VIEWER_API_KEY" in r.stderr


def test_nonexistent_file_fails_before_network():
    # Scenario 3: a dummy key passes the key check; the file-existence check then fails before
    # any network call (cmd_upload checks exists() before do_upload). Exit 1, file-not-found.
    env = {**os.environ, "NUTRIENT_DWS_VIEWER_API_KEY": "pdf_live_dummy"}
    r = subprocess.run([sys.executable, str(SCRIPT), "upload", "--file", "/nonexistent-xyz.pdf"],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 1
    assert "not found" in r.stderr.lower()


def test_no_global_key_fallback_when_viewer_key_unset():
    # RK-03: NUTRIENT_API_KEY must NOT be used when the viewer key is unset and no opt-in flag.
    env = {**os.environ, "NUTRIENT_API_KEY": "pdf_live_globaldecoy"}
    env.pop("NUTRIENT_DWS_VIEWER_API_KEY", None)
    r = subprocess.run([sys.executable, str(SCRIPT), "upload", "--file", "x.pdf"],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 1
    assert "NUTRIENT_DWS_VIEWER_API_KEY" in r.stderr
    assert "globaldecoy" not in (r.stdout + r.stderr)


def test_allow_global_key_opt_in_uses_fallback():
    # RK-03 opt-in: with --allow-global-key and the viewer key unset, NUTRIENT_API_KEY is used and
    # a fallback warning is emitted. Drive it to a fast pre-network exit via a nonexistent file.
    env = {**os.environ, "NUTRIENT_API_KEY": "pdf_live_global"}
    env.pop("NUTRIENT_DWS_VIEWER_API_KEY", None)
    r = subprocess.run([sys.executable, str(SCRIPT), "--allow-global-key", "upload",
                        "--file", "/nonexistent-xyz.pdf"], capture_output=True, text=True, env=env)
    assert r.returncode == 1
    # The fallback warning fires (key resolved); it does NOT bail with "is not set".
    assert "falling back to NUTRIENT_API_KEY" in r.stderr
    assert "is not set" not in r.stderr
    # And it then fails on the missing file, not the key — proving the fallback resolved a key.
    assert "not found" in r.stderr.lower()
    assert "pdf_live_global" not in (r.stdout + r.stderr), "fallback key value must not leak"


# --- review-fix regressions --------------------------------------------------------------
def test_malformed_jwt_shape_triggers_cleanup(tmp_path, capsys):
    # P1 (review): a 2xx session whose "jwt" is a non-string (dict/number) must not TypeError
    # past cleanup and orphan the upload — it routes to the missing-jwt cleanup path.
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4 minimal")
    handler, calls = _upload_then_session(httpx.Response(200, json={"jwt": {"nested": "oops"}}))
    with _client(handler) as c, pytest.raises(SystemExit) as e:
        vs.cmd_upload_and_session(c, "KEY", _Args(file=str(f), jwt_out=str(tmp_path / "j.txt")))
    assert e.value.code == 1
    assert ("DELETE", "/viewer/documents/DOC1") in calls, "malformed jwt orphaned the upload"


def test_upload_and_session_happy_path_pins_wire_contract(tmp_path, capsys):
    # P2 (review): positive combined-flow — assert exact methods/paths, bearer header, upload
    # content-type, least-privilege permission body, and a bounded exp.
    import time
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4 minimal")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.setdefault("auth", request.headers.get("Authorization"))
        if request.method == "POST" and request.url.path == "/viewer/documents":
            seen["upload_ct"] = request.headers.get("Content-Type")
            return httpx.Response(200, json={"data": {"document_id": "DOC1"}})
        if request.method == "POST" and request.url.path == "/viewer/sessions":
            seen["session_body"] = json.loads(request.content)
            return httpx.Response(201, json={"jwt": "a.b.c"})
        return httpx.Response(404)

    with _client(handler) as c:
        vs.cmd_upload_and_session(c, "KEY", _Args(file=str(f)))
    assert seen["auth"] == "Bearer KEY"
    assert seen["upload_ct"] == "application/octet-stream"
    doc = seen["session_body"]["allowed_documents"][0]
    assert doc["document_id"] == "DOC1"
    assert doc["permissions"] == ["read"], "least-privilege default not honored"
    exp = seen["session_body"]["exp"]
    assert isinstance(exp, int) and 0 < exp - int(time.time()) <= vs.MAX_EXPIRES_IN, "exp not bounded"


if __name__ == "__main__":
    sys.exit(pytest.main([str(Path(__file__)), "-q"]))
