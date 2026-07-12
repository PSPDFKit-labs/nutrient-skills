#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27", "pypdf>=4.0"]
# ///
"""Auto-tag a PDF with PDF/UA semantic structure via the Nutrient DWS Accessibility API.

POSTs to https://api.nutrient.io/accessibility/autotag (multipart for local files, JSON body
for --url) and writes the remediated, tagged PDF to --output.

Transport note: this calls the endpoint directly with httpx rather than through the nutrient-dws
SDK — that SDK exposes no Accessibility method (see the skill's KD8). The DWS Accessibility API is
a separate product with its own key (NUTRIENT_ACCESSIBILITY_API_KEY); a Processor or Extraction
key returns 401. There is no silent fallback to NUTRIENT_API_KEY: a missing Accessibility key is a
hard error so the failure is obvious rather than masked.

Quota: auto-tagging consumes from the monthly auto-tagged-pages quota (Free tier = 20/month, no
rollover). The script gates runs above --confirm-over (default 20) unless --yes is passed.
"""

import argparse
import asyncio
import ipaddress
import json
import os
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

AUTOTAG_URL = "https://api.nutrient.io/accessibility/autotag"
MAX_BYTES = 150 * 1024 * 1024  # 150 MiB
DEFAULT_CONFIRM_OVER = 20  # Free-tier monthly auto-tagged-pages bucket


# --------------------------------------------------------------------------------------------
# Pure helpers (no network / key) — unit-tested.
# --------------------------------------------------------------------------------------------
def validate_input(path: Path) -> None:
    """Raise ValueError when the local input is missing, not a PDF, or over the size limit."""
    if not path.exists():
        raise ValueError(f"input file not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"input must be a .pdf file: {path}")
    size = path.stat().st_size
    if size > MAX_BYTES:
        raise ValueError(
            f"input is {size / 1024 / 1024:.1f} MiB, over the 150 MiB limit. "
            "Split it first with document-processor-api/split.py."
        )


def validate_remote_url(url: str) -> None:
    """Raise ValueError unless the URL is https and resolves to a public host (R18, anti-SSRF)."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("--url must use https://")
    host = parsed.hostname
    if not host or host.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        raise ValueError("--url host is not allowed")
    # Resolve and require a globally-routable public address. is_global is the positive check:
    # it rejects private, loopback, link-local, reserved, multicast, and unspecified ranges in one
    # test, rather than enumerating exclusions and missing a class.
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise ValueError(f"--url host does not resolve: {host}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise ValueError(f"--url resolves to a non-public address ({ip}); refused")


def local_page_count(path: Path):
    """Best-effort page count for the quota gate; None if it cannot be read."""
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(path)).pages)
    except Exception:
        return None


def quota_gate(pages, confirm_over: int, yes: bool, interactive: bool) -> tuple[bool, str]:
    """Decide whether to proceed given the estimated page count (R16 / KD6).

    Remaining quota is not surfaced pre-call, so the gate is anchored to --confirm-over
    (default 20, the Free-tier monthly bucket). Returns (proceed, message).

    Unknown page count (pages is None — a remote --url, or an unreadable local file) does NOT
    auto-proceed: an unbounded remote PDF could otherwise burn quota with no confirmation. Unknown
    count requires --yes (or interactive confirmation), same as exceeding the threshold.
    """
    if yes or (pages is not None and pages <= confirm_over):
        return True, ""
    if pages is None:
        msg = (
            "Preflight: page count is unknown (remote --url or unreadable file), so auto-tagging "
            "quota cost can't be bounded. Auto-tagging consumes quota that does not roll over. "
            "Re-run with --yes to proceed."
        )
    else:
        msg = (
            f"Preflight: {pages} page(s) exceeds --confirm-over {confirm_over} "
            f"(the Free-tier monthly auto-tagged-pages bucket). Auto-tagging consumes quota that "
            "does not roll over. Re-run with --yes to proceed."
        )
    if interactive:
        return input(f"{msg}\nProceed anyway? [y/N] ").strip().lower() in ("y", "yes"), msg
    return False, msg


def redact(text: str, secret: str | None) -> str:
    """Remove the API key from text before printing (in case an error echoes request headers)."""
    if secret and secret in text:
        return text.replace(secret, "[REDACTED]")
    return text


def is_pdf_response(content: bytes, content_type: str) -> bool:
    """True when a 2xx response actually carries a PDF, guarding against a proxy/gateway 2xx
    HTML/JSON page being written out as a corrupt 'PDF'. PDF magic bytes or an application/pdf
    content-type both qualify."""
    return content[:4] == b"%PDF" or "application/pdf" in (content_type or "").lower()


def quota_note(build_stats_header: str | None, fallback_pages) -> str:
    """Build the quota-consumption note from the response's x-pspdfkit-build-stats header (R14)."""
    if build_stats_header:
        try:
            stats = json.loads(build_stats_header)
            pages = stats.get("output", {}).get("page_count")
            units = (
                stats.get("required_license_features", {})
                .get("pdf_to_pdfua_api", {})
                .get("units")
            )
            if pages is not None:
                unit_str = f", {units} quota unit(s)" if units is not None else ""
                return f"Auto-tagged {pages} page(s){unit_str}."
        except (ValueError, TypeError):
            pass
    if fallback_pages is not None:
        return f"Auto-tagged ~{fallback_pages} page(s) (estimated from local file)."
    return "Auto-tagging complete (page count not surfaced by the API)."


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Auto-tag a PDF with PDF/UA structure via the Nutrient DWS Accessibility API.",
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", help="Local PDF to auto-tag.")
    src.add_argument("--url", help="Remote PDF URL (https only) to auto-tag.")
    p.add_argument("--output", help="Output path. Default: <input-stem>-tagged.pdf.")
    p.add_argument("--confirm-over", dest="confirm_over", type=int, default=DEFAULT_CONFIRM_OVER,
                   help="Confirm before runs exceeding this many pages (default 20).")
    p.add_argument("--yes", action="store_true", help="Bypass the quota confirmation gate.")
    return p


def _require_key() -> str:
    key = os.environ.get("NUTRIENT_ACCESSIBILITY_API_KEY")
    if not key:  # None or empty — an empty key would send "Authorization: Bearer " and 401
        print(
            "NUTRIENT_ACCESSIBILITY_API_KEY is not set. The DWS Accessibility API is a separate "
            "product with its own key (not the Processor or Extraction key). Export it before "
            "running this script.",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def _resolve_output(args) -> Path:
    if args.output:
        return Path(args.output)
    if args.input:
        stem = Path(args.input)
        return stem.with_name(f"{stem.stem}-tagged.pdf")
    return Path("tagged.pdf")


async def main() -> None:
    args = build_parser().parse_args()
    key = _require_key()

    # Input validation (R6, R9, R18) before any network call.
    try:
        if args.input:
            in_path = Path(args.input)
            validate_input(in_path)
            pages = local_page_count(in_path)
        else:
            validate_remote_url(args.url)
            pages = None  # cannot count a remote file locally
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Quota gate (R16 / KD6).
    proceed, message = quota_gate(pages, args.confirm_over, args.yes, sys.stdin.isatty())
    if not proceed:
        print(message, file=sys.stderr)
        sys.exit(2)

    # Preflight the output target before the billable POST, so a bad --output path fails before
    # consuming auto-tagging quota rather than after.
    out_path = _resolve_output(args)
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error: cannot create output directory {out_path.parent}: {e}", file=sys.stderr)
        sys.exit(1)
    if not os.access(out_path.parent, os.W_OK):
        print(f"Error: output directory is not writable: {out_path.parent}", file=sys.stderr)
        sys.exit(1)
    if out_path.is_symlink():
        print(f"Error: --output is a symlink; refusing to follow it: {out_path}", file=sys.stderr)
        sys.exit(1)
    if out_path.is_dir():
        print(f"Error: --output is a directory, not a file: {out_path}", file=sys.stderr)
        sys.exit(1)

    import httpx

    headers = {"Authorization": f"Bearer {key}"}
    async with httpx.AsyncClient(timeout=180) as client:
        if args.input:
            file_bytes = Path(args.input).read_bytes()
            file_name = Path(args.input).name
        else:
            # Fetch the URL client-side and upload the bytes, rather than handing the URL to the
            # Nutrient backend to fetch. A backend fetch can't be defended against DNS-rebinding
            # from this client (the host could resolve public at our check and private at the
            # backend's fetch); not performing a backend fetch removes that boundary entirely.
            # Re-validate post-resolution and disable redirects (a 3xx to an internal target is
            # rejected as a non-2xx below).
            validate_remote_url(args.url)
            # Stream the body and abort the moment it exceeds the cap, so a large or endless URL
            # can't exhaust memory before the size check (the buffer-then-check order would).
            buf = bytearray()
            async with client.stream("GET", args.url, follow_redirects=False) as dl:
                if dl.status_code // 100 != 2:
                    print(f"Error: could not fetch --url (HTTP {dl.status_code}); redirects are "
                          "not followed.", file=sys.stderr)
                    sys.exit(1)
                async for piece in dl.aiter_bytes():
                    buf += piece
                    if len(buf) > MAX_BYTES:
                        print("Error: --url body exceeds the 150 MiB limit; download aborted.",
                              file=sys.stderr)
                        sys.exit(1)
            file_bytes = bytes(buf)
            file_name = Path(urlparse(args.url).path).name or "remote.pdf"

        files = {"file": (file_name, file_bytes, "application/pdf")}
        resp = await client.post(AUTOTAG_URL, headers=headers, files=files)

    if resp.status_code // 100 != 2:
        body = redact(resp.text, key)
        print(f"Error: HTTP {resp.status_code}\n{body}", file=sys.stderr)
        sys.exit(1)

    # A 2xx is not proof of a PDF: a proxy/gateway/WAF can return a 2xx HTML or JSON page that
    # would otherwise be written out as a corrupt "PDF" and reported as success. Require the PDF
    # magic bytes (or an application/pdf content-type) before writing.
    ctype = resp.headers.get("content-type", "")
    if not is_pdf_response(resp.content, ctype):
        excerpt = redact(resp.text[:500], key) if resp.content[:1] in (b"{", b"<", b" ", b"\n") \
            else f"<{len(resp.content)} bytes>"
        print(f"Error: expected a PDF but the response was content-type '{ctype}'.\n{excerpt}",
              file=sys.stderr)
        sys.exit(1)

    # Write atomically at 0600, refusing a symlinked target (O_NOFOLLOW): the remediated document
    # is as sensitive as the input, and the parent dir was preflighted before the POST.
    fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as f:
        os.fchmod(f.fileno(), 0o600)
        f.write(resp.content)
    print(f"Wrote {out_path}")
    print(quota_note(resp.headers.get("x-pspdfkit-build-stats"), pages), file=sys.stderr)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:  # noqa: BLE001
        print(str(e), file=sys.stderr)
        sys.exit(1)
