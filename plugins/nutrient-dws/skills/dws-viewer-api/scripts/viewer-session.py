#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27"]
# ///
"""Cloud-side operations for the Nutrient DWS Viewer API: upload a document and mint a
browser viewer session JWT.

Three server-side primitives, one script:
  upload              Upload a document to Nutrient storage; print its document_id.
  session             Mint a session JWT for a DWS-managed document (or --app-provided).
  upload-and-session  Upload then mint in one shot (the common case + live smoke path).

Transport note: this calls the endpoints directly with httpx. The nutrient-dws SDK targets
the Processor/Extraction products and exposes no Viewer methods; if it adds them, swap the
httpx calls at the marked sites.

Security:
  - The DWS Viewer API is a separate product with its own key (NUTRIENT_DWS_VIEWER_API_KEY).
    There is NO silent fallback to NUTRIENT_API_KEY — a wrong-product key could mint a real
    browser JWT against the wrong tenant with no signal. A global DWS key must be opted into
    explicitly via --allow-global-key.
  - Sessions default to ["read"] (least privilege). write/download require explicit flags.
  - The session JWT is a bearer credential. It is printed ONCE to stdout for capture and is
    never logged at debug level; the API key is redacted from error output. stdout is captured
    in CI logs and agent transcripts — for automation prefer --jwt-out <file> (written 0600).
"""

import argparse
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

BASE_URL = "https://api.nutrient.io"
DOCUMENTS_URL = f"{BASE_URL}/viewer/documents"
SESSIONS_URL = f"{BASE_URL}/viewer/sessions"

DEFAULT_EXPIRES_IN = 3600  # 1 hour — conservative default (generate-a-session-token guide)
MAX_EXPIRES_IN = 24 * 3600  # 24h documented ceiling
SHORT_TTL_WARN = 3600  # warn above 1h: a leaked long-TTL JWT is an open exfiltration window


# --------------------------------------------------------------------------------------------
# Pure helpers (no network / key) — unit-tested.
# --------------------------------------------------------------------------------------------
def resolve_permissions(allow_write: bool, allow_download: bool, permissions: str | None) -> list[str]:
    """Resolve the session permission list. Least privilege: default ["read"] (R-15).

    An explicit --permissions list wins outright. Otherwise start from ["read"] and add
    write/download only when their opt-in flags are set.
    """
    if permissions is not None:
        perms = [p.strip() for p in permissions.split(",") if p.strip()]
        return perms or ["read"]
    perms = ["read"]
    if allow_write:
        perms.append("write")
    if allow_download:
        perms.append("download")
    return perms


def clamp_expires_in(expires_in: int) -> tuple[int, str | None]:
    """Clamp --expires-in into (0, MAX_EXPIRES_IN]; return (value, warning-or-None).

    A non-positive TTL would mint an already-expired session (a dead-on-arrival JWT that still
    consumes quota and, in upload-and-session, creates then orphans a document), so it is floored
    to the default rather than passed through.
    """
    warn = None
    if expires_in <= 0:
        return DEFAULT_EXPIRES_IN, (
            f"--expires-in must be positive; using the default {DEFAULT_EXPIRES_IN}s (1h)."
        )
    if expires_in > MAX_EXPIRES_IN:
        warn = (
            f"--expires-in {expires_in}s exceeds the {MAX_EXPIRES_IN}s (24h) ceiling; "
            f"clamping to {MAX_EXPIRES_IN}s."
        )
        expires_in = MAX_EXPIRES_IN
    elif expires_in > SHORT_TTL_WARN:
        warn = (
            f"--expires-in {expires_in}s is over {SHORT_TTL_WARN}s (1h). A leaked session JWT is "
            "valid until it expires; prefer a short TTL for high-sensitivity documents."
        )
    return expires_in, warn


def build_session_body(document_id: str | None, permissions: list[str], expires_in: int) -> dict:
    """Build the POST /viewer/sessions body. Empty {} for app-provided; allowed_documents
    otherwise. exp is an absolute unix timestamp = now + expires_in."""
    if document_id is None:
        return {}
    return {
        "allowed_documents": [{"document_id": document_id, "permissions": permissions}],
        "exp": int(time.time()) + expires_in,
    }


def redact(text: str, secret: str | None) -> str:
    """Remove the API key from text before printing (error bodies may echo request headers)."""
    if secret and secret in text:
        return text.replace(secret, "[REDACTED]")
    return text


# --------------------------------------------------------------------------------------------
# Key handling
# --------------------------------------------------------------------------------------------
def require_key(allow_global_key: bool) -> str:
    """Return the Viewer API key. No silent NUTRIENT_API_KEY fallback (RK-03, Decision 3)."""
    key = os.environ.get("NUTRIENT_DWS_VIEWER_API_KEY")
    if key is not None and key != "":
        return key
    if allow_global_key:
        global_key = os.environ.get("NUTRIENT_API_KEY")
        if global_key:
            print(
                "Warning: NUTRIENT_DWS_VIEWER_API_KEY is unset; falling back to NUTRIENT_API_KEY "
                "because --allow-global-key was passed. This only works if your tenant has migrated "
                "to a global DWS key; otherwise it may mint a JWT against the wrong product.",
                file=sys.stderr,
            )
            return global_key
    print(
        "NUTRIENT_DWS_VIEWER_API_KEY is not set. The DWS Viewer API is a separate product with its "
        "own key (not the Processor key NUTRIENT_API_KEY or the Extraction key "
        "NUTRIENT_EXTRACT_API_KEY). Export it before running this script. If your tenant uses a "
        "global DWS key, pass --allow-global-key to opt into NUTRIENT_API_KEY explicitly.",
        file=sys.stderr,
    )
    sys.exit(1)


# --------------------------------------------------------------------------------------------
# Network operations (httpx). Swap sites marked [SDK-SWAP] if a Viewer client method lands.
# --------------------------------------------------------------------------------------------
def _auth_headers(key: str) -> dict:
    return {"Authorization": f"Bearer {key}"}


def do_upload(client, key: str, file_path: Path) -> str:
    """Upload a document (binary body, preferred per docs). Return its document_id. [SDK-SWAP]"""
    resp = client.post(
        DOCUMENTS_URL,
        headers={**_auth_headers(key), "Content-Type": "application/octet-stream"},
        content=file_path.read_bytes(),
    )
    if resp.status_code // 100 != 2:
        _fail_http("upload", resp, key)
    data = resp.json().get("data", {})
    document_id = data.get("document_id")
    if not document_id:
        print(f"Error: upload succeeded but no document_id in response: {redact(resp.text, key)}",
              file=sys.stderr)
        sys.exit(1)
    return document_id


def do_delete(client, key: str, document_id: str) -> bool:
    """Best-effort delete of a Nutrient-managed document. Return True on 2xx. [SDK-SWAP]

    Confirmed live (U6): DELETE /viewer/documents/{id} -> 200, hard + synchronous.
    """
    try:
        # Percent-encode the id as a single path segment so a document_id carrying '/' or '..'
        # (an unexpected server value) can't be normalized by httpx into a different endpoint.
        resp = client.delete(f"{DOCUMENTS_URL}/{quote(document_id, safe='')}",
                             headers=_auth_headers(key))
        return resp.status_code // 100 == 2
    except Exception as exc:  # noqa: BLE001 — cleanup is best-effort; never mask the original failure
        # Log why cleanup failed so the operator can tell transient (retry) from permanent
        # (wrong key/account) — the caller still reports the orphan and never raises from here.
        print(f"Warning: cleanup DELETE of {document_id} raised {type(exc).__name__}: "
              f"{redact(str(exc), key)}", file=sys.stderr)
        return False


def _parse_jwt(resp, key: str) -> str | None:
    """Extract the jwt from a 2xx session response. None on a non-JSON body or a missing key.

    A 2xx response whose body is not a JSON object (a non-JSON body, or a JSON array/string/null)
    must not raise uncaught — in upload-and-session that would bypass cleanup and orphan the
    uploaded document.
    """
    try:
        data = resp.json()
    except (ValueError, TypeError):
        return None
    jwt = data.get("jwt") if isinstance(data, dict) else None
    # Only a non-empty STRING is a usable JWT. A dict/number/list "jwt" would reach f.write()
    # and raise TypeError past the OSError-only cleanup — orphaning the uploaded document — so
    # coerce any non-string shape to None and let the missing-jwt cleanup path handle it.
    return jwt if isinstance(jwt, str) and jwt else None


def _cleanup_and_report(client, key: str, document_id: str | None, context: str) -> None:
    """Best-effort delete of an uploaded document + report whether an orphan remains (R-16).

    document_id is None for paths that never uploaded (nothing to clean).
    """
    if document_id is None:
        return
    if do_delete(client, key, document_id):
        print(f"Cleaned up uploaded document {document_id} after {context}.", file=sys.stderr)
    else:
        print(
            f"WARNING: {context}, AND cleanup of uploaded document {document_id} failed. "
            f"Delete it manually: DELETE {DOCUMENTS_URL}/{document_id}",
            file=sys.stderr,
        )


def do_session(client, key: str, body: dict) -> str:
    """Mint a session JWT. Return the JWT string. [SDK-SWAP]"""
    resp = client.post(SESSIONS_URL, headers=_auth_headers(key), json=body)
    if resp.status_code // 100 != 2:
        _fail_http("session", resp, key)
    jwt = _parse_jwt(resp, key)
    if not jwt:
        print(f"Error: session minted but no usable jwt in response: {redact(resp.text, key)}",
              file=sys.stderr)
        sys.exit(1)
    return jwt


def _fail_http(op: str, resp, key: str) -> None:
    body = redact(resp.text, key)[:1000]
    print(f"Error: {op} failed — HTTP {resp.status_code}\n{body}", file=sys.stderr)
    sys.exit(1)


# --------------------------------------------------------------------------------------------
# JWT output — once to stdout, or 0600 file for automation
# --------------------------------------------------------------------------------------------
def validate_jwt_out(jwt_out: str | None) -> None:
    """Pre-flight the --jwt-out target before any upload, so a bad path fails fast and never
    orphans an uploaded document. Rejects a missing parent dir, a directory target, and a symlink
    target (which the O_NOFOLLOW write would reject anyway) — all before the billable session call."""
    if not jwt_out:
        return
    path = Path(jwt_out)
    if not path.parent.exists() or not path.parent.is_dir():
        print(f"Error: --jwt-out directory does not exist: {path.parent}", file=sys.stderr)
        sys.exit(1)
    if path.is_symlink():
        print(f"Error: --jwt-out is a symlink; refusing to follow it: {jwt_out}", file=sys.stderr)
        sys.exit(1)
    if path.is_dir():
        print(f"Error: --jwt-out is a directory, not a file: {jwt_out}", file=sys.stderr)
        sys.exit(1)


def emit_jwt(jwt: str, jwt_out: str | None) -> None:
    if jwt_out:
        # Create/overwrite atomically at 0600, refusing a symlinked target (O_NOFOLLOW) so the
        # bearer credential never lands at a wider mode and a pre-planted symlink can't redirect
        # it. fchmod enforces 0600 even when the file pre-existed at a wider mode (O_CREAT's mode
        # applies only on creation). Overwriting a regular file is allowed (no O_EXCL) so a path
        # can be reused across runs.
        fd = os.open(jwt_out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            os.fchmod(f.fileno(), 0o600)
            f.write(jwt)
        print(f"jwt_written={jwt_out}")
    else:
        # Printed once to stdout for interactive capture. stdout is captured in CI logs and
        # agent transcripts — prefer --jwt-out for automation. Never logged at debug level.
        print(f"jwt={jwt}")


# --------------------------------------------------------------------------------------------
# Subcommand handlers
# --------------------------------------------------------------------------------------------
def cmd_upload(client, key: str, args) -> None:
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    document_id = do_upload(client, key, file_path)
    print(f"document_id={document_id}")


def cmd_session(client, key: str, args) -> None:
    validate_jwt_out(args.jwt_out)
    if args.app_provided:
        print(
            "Warning: --app-provided mints a session with an empty body. Its authorization scope is "
            "unconfirmed and the least-privilege --permissions do NOT attach to this path; a leaked "
            "app-provided JWT's blast radius is unknown. Use DWS-managed mode for least privilege.",
            file=sys.stderr,
        )
        if args.expires_in != DEFAULT_EXPIRES_IN:
            print(
                "Warning: --expires-in does not apply to --app-provided sessions (the body is empty);"
                " the API applies its own default TTL.",
                file=sys.stderr,
            )
        body = build_session_body(None, [], args.expires_in)
        jwt = do_session(client, key, body)
        emit_jwt(jwt, args.jwt_out)
        return

    if not args.document_id:
        print("Error: session requires --document-id (or --app-provided).", file=sys.stderr)
        sys.exit(1)
    perms = resolve_permissions(args.allow_write, args.allow_download, args.permissions)
    expires_in, warn = clamp_expires_in(args.expires_in)
    if warn:
        print(f"Warning: {warn}", file=sys.stderr)
    body = build_session_body(args.document_id, perms, expires_in)
    jwt = do_session(client, key, body)
    emit_jwt(jwt, args.jwt_out)


def cmd_upload_and_session(client, key: str, args) -> None:
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    validate_jwt_out(args.jwt_out)  # fail fast before upload so a bad path can't orphan a doc
    perms = resolve_permissions(args.allow_write, args.allow_download, args.permissions)
    expires_in, warn = clamp_expires_in(args.expires_in)
    if warn:
        print(f"Warning: {warn}", file=sys.stderr)

    document_id = do_upload(client, key, file_path)
    print(f"document_id={document_id}")

    # Every non-success exit of the post-upload session call must tear down the uploaded document
    # (R-16) — a transport error before any response (timeout, DNS/TLS), a non-2xx status, a 2xx
    # with a non-JSON body, or a 2xx missing the jwt key.
    body = build_session_body(document_id, perms, expires_in)
    try:
        resp = client.post(SESSIONS_URL, headers=_auth_headers(key), json=body)
    except Exception as exc:  # noqa: BLE001 — the session call never returned; the upload is orphaned
        _cleanup_and_report(client, key, document_id,
                            f"session request errored ({type(exc).__name__})")
        print(f"Error: session request failed: {redact(str(exc), key)}", file=sys.stderr)
        sys.exit(1)
    if resp.status_code // 100 != 2:
        _cleanup_and_report(client, key, document_id, "session minting failed")
        _fail_http("session", resp, key)

    jwt = _parse_jwt(resp, key)
    if not jwt:
        _cleanup_and_report(client, key, document_id, "session returned no usable jwt")
        print(f"Error: session minted but no usable jwt in response: {redact(resp.text, key)}",
              file=sys.stderr)
        sys.exit(1)

    try:
        emit_jwt(jwt, args.jwt_out)
    except OSError as e:
        # The JWT file write failed AFTER a successful mint. Do NOT fall back to stdout — that would
        # leak the bearer token into the exact CI/transcript sink --jwt-out exists to avoid. Tear the
        # document down (which makes the un-saved token inert) and report without printing the token.
        if do_delete(client, key, document_id):
            print(f"Error: could not write --jwt-out ({type(e).__name__}: {e}). The uploaded "
                  f"document {document_id} was deleted, so the un-saved session token is now inert.",
                  file=sys.stderr)
        else:
            print(f"Error: could not write --jwt-out ({type(e).__name__}: {e}) AND cleanup of "
                  f"document {document_id} failed. A live session token was minted but not saved; "
                  f"rotate NUTRIENT_DWS_VIEWER_API_KEY and delete the document manually: "
                  f"DELETE {DOCUMENTS_URL}/{document_id}", file=sys.stderr)
        sys.exit(1)


def cmd_delete(client, key: str, args) -> None:
    """Tear down a DWS-managed document. Surfaces the internal do_delete so an agent can satisfy
    the SKILL.md teardown Rule without hand-rolling an httpx call."""
    if do_delete(client, key, args.document_id):
        print(f"deleted={args.document_id}")
    else:
        print(f"Error: delete failed for {args.document_id} (it may not exist, or the key/network "
              "failed — see any warning above).", file=sys.stderr)
        sys.exit(1)


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------
def _add_session_perm_args(p) -> None:
    p.add_argument("--allow-write", action="store_true",
                   help="Grant write permission (default is read-only, least privilege).")
    p.add_argument("--allow-download", action="store_true",
                   help="Grant download permission (default is read-only).")
    p.add_argument("--permissions",
                   help="Explicit comma-separated permission list (e.g. read,write,download). "
                        "Overrides --allow-write/--allow-download. Default: read.")
    p.add_argument("--expires-in", type=int, default=DEFAULT_EXPIRES_IN,
                   help=f"Session TTL in seconds (default {DEFAULT_EXPIRES_IN} = 1h; "
                        f"ceiling {MAX_EXPIRES_IN} = 24h).")
    p.add_argument("--jwt-out",
                   help="Write the JWT to this file (mode 0600) instead of stdout. "
                        "Preferred for automation — stdout is captured in CI logs/transcripts.")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Upload documents and mint viewer session JWTs via the Nutrient DWS Viewer API.",
    )
    p.add_argument("--allow-global-key", action="store_true",
                   help="Opt into NUTRIENT_API_KEY fallback when NUTRIENT_DWS_VIEWER_API_KEY is "
                        "unset (only valid on tenants migrated to a global DWS key).")
    sub = p.add_subparsers(dest="command", required=True)

    up = sub.add_parser("upload", help="Upload a document; print its document_id.")
    up.add_argument("--file", required=True, help="Local document to upload.")

    se = sub.add_parser("session", help="Mint a session JWT for a document (or --app-provided).")
    grp = se.add_mutually_exclusive_group(required=True)
    grp.add_argument("--document-id", help="document_id of a DWS-managed document.")
    grp.add_argument("--app-provided", action="store_true",
                     help="Mint a session with an empty body (app-provided document mode).")
    _add_session_perm_args(se)

    us = sub.add_parser("upload-and-session",
                        help="Upload a document then mint its session JWT (one-shot).")
    us.add_argument("--file", required=True, help="Local document to upload.")
    _add_session_perm_args(us)

    de = sub.add_parser("delete", help="Delete a DWS-managed document (teardown).")
    de.add_argument("--document-id", required=True, help="document_id to delete.")

    return p


def main() -> None:
    args = build_parser().parse_args()
    key = require_key(getattr(args, "allow_global_key", False))

    import httpx

    with httpx.Client(timeout=180) as client:
        if args.command == "upload":
            cmd_upload(client, key, args)
        elif args.command == "session":
            cmd_session(client, key, args)
        elif args.command == "upload-and-session":
            cmd_upload_and_session(client, key, args)
        elif args.command == "delete":
            cmd_delete(client, key, args)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        # Prefix the type so opaque exceptions (e.g. MemoryError stringifies to "") are not a
        # blank line in CI/agent logs. The deliberate error sites above redact the key from HTTP
        # bodies; httpx exception strings do not carry the Authorization header.
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
