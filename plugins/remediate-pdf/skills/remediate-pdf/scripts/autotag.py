#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27", "pypdf>=7.1.1"]
# ///
"""Auto-tag a PDF with PDF/UA semantic structure via the Nutrient Accessibility API.

POSTs to https://api.nutrient.io/accessibility/autotag (multipart, field `file`) and writes the
tagged PDF to --output.

Transport note: this calls the endpoint directly with httpx rather than through the nutrient-dws
SDK, which exposes no Accessibility method. The key is read from NUTRIENT_ACCESSIBILITY_API_KEY,
falling back to NUTRIENT_API_KEY; on current plans, one Nutrient account and key cover the
Accessibility API and the Processor API. A missing key is a hard error so the failure is obvious.

Cost: auto-tagging is billed per page from the account's monthly usage, then the wallet. The
script asks for confirmation above --confirm-over pages (default 10) unless --yes is passed.

Exit codes: 0 = tagged PDF written, 1 = error, 2 = stopped at the cost gate (re-run with --yes
after the user confirms), 4 = the PDF has no text layer and needs OCR first (--allow-no-text
overrides).

This module also holds the helpers validate.py imports: key handling, the client-side URL fetch,
output-path checks, private file writes, and error redaction.
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
DEFAULT_CONFIRM_OVER = 10  # pages; confirm before larger billable runs
DOWNLOAD_DEADLINE = 300  # seconds for the whole --url download, not per read
KEY_VARS = ("NUTRIENT_ACCESSIBILITY_API_KEY", "NUTRIENT_API_KEY")

EXIT_ERROR = 1
EXIT_COST_GATE = 2
EXIT_NO_TEXT = 4

# NAT64 prefixes embed an IPv4 address in an IPv6 one; Python's is_global doesn't look inside.
_NAT64_NETS = (ipaddress.ip_network("64:ff9b::/96"), ipaddress.ip_network("64:ff9b:1::/48"))


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
            f"input is {size / 1024 / 1024:.1f} MiB, over the 150 MiB limit. Split it first "
            "with document-processor-api's split.py (/plugin install nutrient-dws@nutrient-skills)."
        )


def is_public_ip(ip) -> bool:
    """True for a globally routable address, including the IPv4 inside a NAT64 or mapped IPv6."""
    ip = ipaddress.ip_address(ip)
    if ip.version == 6:
        if ip.ipv4_mapped:
            return is_public_ip(ip.ipv4_mapped)
        if any(ip in net for net in _NAT64_NETS):
            return is_public_ip(ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF))
    return ip.is_global


def validate_remote_url(url: str) -> None:
    """Raise ValueError unless the URL is https on port 443 and resolves only to public hosts."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("--url must use https://")
    try:
        port = parsed.port
    except ValueError as e:
        raise ValueError("--url has an invalid port") from e
    if port not in (None, 443):
        raise ValueError("--url must use the default https port (443)")
    host = parsed.hostname
    if not host or host.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        raise ValueError("--url host is not allowed")
    try:
        infos = socket.getaddrinfo(host, 443)
    except socket.gaierror as e:
        raise ValueError(f"--url host does not resolve: {host}") from e
    for info in infos:
        if not is_public_ip(info[4][0]):
            raise ValueError(f"--url resolves to a non-public address ({info[4][0]}); refused")


def local_page_count(path: Path):
    """Best-effort page count for the quota gate; None if it cannot be read."""
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(path)).pages)
    except Exception:
        return None


def quota_gate(pages, confirm_over: int, yes: bool, interactive: bool,
               operation: str = "Auto-tagging") -> tuple[bool, str]:
    """Decide whether to proceed given the estimated page count. Returns (proceed, message).

    Remaining usage is not surfaced pre-call, so the gate is anchored to --confirm-over. An
    unknown page count (a remote --url, or an unreadable local file) does NOT auto-proceed: an
    unbounded remote PDF could otherwise run up cost with no confirmation.
    """
    if yes or (pages is not None and pages <= confirm_over):
        return True, ""
    if pages is None:
        msg = (
            f"Preflight: page count is unknown (remote --url or unreadable file), so the cost of "
            f"{operation.lower()} can't be bounded. {operation} is billed per page "
            "(rates: https://www.nutrient.io/api/pricing/). "
            "Ask the user, then re-run with --yes to proceed."
        )
    else:
        msg = (
            f"Preflight: {pages} page(s) exceeds --confirm-over {confirm_over}. {operation} is "
            "billed per page from your monthly usage, then your wallet "
            "(rates: https://www.nutrient.io/api/pricing/). "
            "Ask the user, then re-run with --yes to proceed."
        )
    if interactive:
        return input(f"{msg}\nProceed anyway? [y/N] ").strip().lower() in ("y", "yes"), msg
    return False, msg


def has_text_layer(path: Path, max_pages: int = 3):
    """True if any of the first pages has extractable text, False if none do (likely an
    image-only scan that needs OCR first), None if the file can't be read. Only the first
    max_pages pages are checked, so a mostly-text PDF with some scanned pages reads as True."""
    try:
        from pypdf import PdfReader

        for page in PdfReader(str(path)).pages[:max_pages]:
            if (page.extract_text() or "").strip():
                return True
        return False
    except Exception:
        return None


def normalize_key(raw: str | None) -> str | None:
    """Strip surrounding whitespace (a pasted key or a CRLF .env line) and return the key, or None
    when empty. Raise ValueError when what's left can't be sent as a header, so the key is never
    echoed back by the HTTP library's own error."""
    if raw is None:
        return None
    key = raw.strip()
    if not key:
        return None
    if not all(33 <= ord(c) < 127 for c in key):
        raise ValueError("contains spaces or characters an API key can't have")
    return key


def redact(text: str, *secrets: str | None) -> str:
    """Remove secrets (the API key, a PDF password) from text before printing it."""
    for secret in secrets:
        if secret and secret in text:
            text = text.replace(secret, "[REDACTED]")
    return text


def is_pdf_response(content: bytes, content_type: str) -> bool:
    """True when a 2xx response actually carries a PDF, guarding against a proxy/gateway 2xx
    HTML/JSON page being written out as a corrupt 'PDF'. PDF magic bytes or an application/pdf
    content-type both qualify."""
    return content[:4] == b"%PDF" or "application/pdf" in (content_type or "").lower()


def quota_note(build_stats_header: str | None, fallback_pages) -> str:
    """Build the usage note from the response's x-pspdfkit-build-stats header."""
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


def check_output_path(out_path: Path, input_path: Path | None, overwrite: bool) -> None:
    """Raise ValueError unless out_path is safe to write before a billable call: not a symlink
    or directory, not the input file, not an existing file (unless overwrite), in a writable
    directory (created if missing)."""
    if out_path.is_symlink():
        raise ValueError(f"output is a symlink; refusing to follow it: {out_path}")
    if out_path.is_dir():
        raise ValueError(f"output is a directory, not a file: {out_path}")
    if input_path is not None and out_path.resolve() == input_path.resolve():
        raise ValueError(f"output would overwrite the input file: {out_path}")
    if out_path.exists() and not overwrite:
        raise ValueError(f"output already exists: {out_path} (pass --overwrite to replace it)")
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ValueError(f"cannot create output directory {out_path.parent}: {e}") from e
    if not os.access(out_path.parent, os.W_OK):
        raise ValueError(f"output directory is not writable: {out_path.parent}")


def write_private(path: Path, data: bytes, overwrite: bool) -> None:
    """Write data at 0600 without following a symlink. Without overwrite, an existing file is
    refused (O_EXCL); with it, an existing file is truncated and its mode reset to 0600."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | (os.O_TRUNC if overwrite else os.O_EXCL)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as f:
        os.fchmod(f.fileno(), 0o600)
        f.write(data)


def secrets_from_env() -> list[str]:
    """Every configured secret, raw and stripped, for redacting unexpected errors."""
    values = [os.environ.get(v) for v in (*KEY_VARS, "NUTRIENT_PDF_PASSWORD")]
    return [s for v in values if v for s in {v, v.strip()} if s]


# --------------------------------------------------------------------------------------------
# Shared I/O (key, remote fetch)
# --------------------------------------------------------------------------------------------
def require_key() -> str:
    """Return the API key from NUTRIENT_ACCESSIBILITY_API_KEY or NUTRIENT_API_KEY, or exit 1."""
    for var in KEY_VARS:
        try:
            key = normalize_key(os.environ.get(var))
        except ValueError as e:
            print(f"Error: {var} {e}. Check the value you exported.", file=sys.stderr)
            sys.exit(EXIT_ERROR)
        if key:
            return key
    print(
        "NUTRIENT_ACCESSIBILITY_API_KEY is not set. Export your Nutrient API key (or set "
        "NUTRIENT_API_KEY) before running this script.",
        file=sys.stderr,
    )
    sys.exit(EXIT_ERROR)


async def fetch_remote_pdf(client, url: str) -> tuple[bytes, str]:
    """Download a remote PDF client-side and return (bytes, file name). Raise ValueError on any
    refusal.

    The Nutrient backend never fetches the URL. Safeguards: https on port 443 only, every
    resolved address public, the address actually connected to re-checked (DNS rebinding),
    redirects not followed, the body capped at MAX_BYTES while streaming, and one deadline for
    the whole download so a slow server can't hang the agent.
    """
    validate_remote_url(url)

    async def _download() -> bytes:
        buf = bytearray()
        async with client.stream("GET", url, follow_redirects=False) as dl:
            stream = dl.extensions.get("network_stream")
            addr = stream.get_extra_info("server_addr") if stream else None
            if not addr or not is_public_ip(addr[0]):
                raise ValueError("--url connected to a non-public address; refused")
            if dl.status_code // 100 != 2:
                raise ValueError(
                    f"could not fetch --url (HTTP {dl.status_code}); redirects are not followed"
                )
            async for piece in dl.aiter_bytes():
                buf += piece
                if len(buf) > MAX_BYTES:
                    raise ValueError("--url body exceeds the 150 MiB limit; download aborted")
        return bytes(buf)

    try:
        data = await asyncio.wait_for(_download(), timeout=DOWNLOAD_DEADLINE)
    except asyncio.TimeoutError as e:
        raise ValueError(f"--url download took longer than {DOWNLOAD_DEADLINE}s; aborted") from e
    return data, Path(urlparse(url).path).name or "remote.pdf"


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Auto-tag a PDF with PDF/UA structure via the Nutrient Accessibility API.",
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", help="Local PDF to auto-tag.")
    src.add_argument("--url", help="Remote PDF URL (https only) to auto-tag.")
    p.add_argument("--output", help="Output path. Default: <input-stem>-tagged.pdf.")
    p.add_argument("--overwrite", action="store_true", help="Replace --output if it exists.")
    p.add_argument("--confirm-over", dest="confirm_over", type=int, default=DEFAULT_CONFIRM_OVER,
                   help=f"Confirm before runs exceeding this many pages (default {DEFAULT_CONFIRM_OVER}).")
    p.add_argument("--yes", action="store_true",
                   help="Bypass the cost confirmation gate (only after the user has confirmed).")
    p.add_argument("--allow-no-text", dest="allow_no_text", action="store_true",
                   help="Auto-tag even when the PDF has no text layer (normally exit 4: OCR first).")
    return p


def _resolve_output(args) -> Path:
    if args.output:
        return Path(args.output)
    if args.input:
        stem = Path(args.input)
        return stem.with_name(f"{stem.stem}-tagged.pdf")
    return Path("tagged.pdf")


async def main() -> None:
    args = build_parser().parse_args()
    key = require_key()

    # Input validation before any network call.
    in_path = Path(args.input) if args.input else None
    try:
        if in_path:
            validate_input(in_path)
            pages = local_page_count(in_path)
        else:
            validate_remote_url(args.url)
            pages = None  # cannot count a remote file locally
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    if in_path and not args.allow_no_text and has_text_layer(in_path) is False:
        print(
            "Error: this PDF has no text layer (likely a scan). Auto-tagging doesn't add one, so "
            "the result would have no readable text. Run OCR first with document-processor-api: "
            "`uv run scripts/ocr.py --input <file> --languages english --out <file>-ocr.pdf`, "
            "then auto-tag the OCR'd file. Pass --allow-no-text to auto-tag anyway.",
            file=sys.stderr,
        )
        sys.exit(EXIT_NO_TEXT)

    proceed, message = quota_gate(pages, args.confirm_over, args.yes, sys.stdin.isatty())
    if not proceed:
        print(message, file=sys.stderr)
        sys.exit(EXIT_COST_GATE)

    # Preflight the output target before the billable POST.
    out_path = _resolve_output(args)
    try:
        check_output_path(out_path, in_path, args.overwrite)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    import httpx

    headers = {"Authorization": f"Bearer {key}"}
    async with httpx.AsyncClient(timeout=180) as client:
        if in_path:
            file_bytes, file_name = in_path.read_bytes(), in_path.name
        else:
            try:
                file_bytes, file_name = await fetch_remote_pdf(client, args.url)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(EXIT_ERROR)
        files = {"file": (file_name, file_bytes, "application/pdf")}
        resp = await client.post(AUTOTAG_URL, headers=headers, files=files)

    if resp.status_code // 100 != 2:
        hint = {
            401: "The API key is missing or invalid. Accounts created before the unified plan "
                 "(16 Nov 2026) may have separate keys per API; check the dashboard.",
            402: "The account's usage is used up. Add funds to the wallet or wait for the reset.",
        }.get(resp.status_code, "")
        print(f"Error: HTTP {resp.status_code}. {hint}\n{redact(resp.text, key)}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    # A 2xx is not proof of a PDF: a proxy/gateway/WAF can return a 2xx HTML or JSON page.
    ctype = resp.headers.get("content-type", "")
    if not is_pdf_response(resp.content, ctype):
        excerpt = redact(resp.text[:500], key) if resp.content[:1] in (b"{", b"<", b" ", b"\n") \
            else f"<{len(resp.content)} bytes>"
        print(f"Error: expected a PDF but the response was content-type '{ctype}'.\n{excerpt}",
              file=sys.stderr)
        sys.exit(EXIT_ERROR)

    write_private(out_path, resp.content, args.overwrite)
    print(f"Wrote {out_path}")
    print(quota_note(resp.headers.get("x-pspdfkit-build-stats"), pages), file=sys.stderr)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"Error: {redact(str(e), *secrets_from_env())}", file=sys.stderr)
        sys.exit(EXIT_ERROR)
