#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27"]
# ///
"""Validate a PDF against PDF/UA-1 via the Nutrient Accessibility API.

POSTs to https://api.nutrient.io/accessibility/validate_pdfua (multipart, field `file`) and writes
the JSON validation report to --report. Prints a plain-language summary of every failed check.

A completed validation returns HTTP 200 whether or not the PDF conforms, so the result comes from
`isValid` in the body, not the status code. Exit codes: 0 = conforms to PDF/UA-1, 3 = does not
conform (report written), 1 = error (nothing validated).

Each validation is billed per operation from the account's monthly usage, then the wallet.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))
from autotag import MAX_BYTES, redact, validate_input, validate_remote_url  # noqa: E402

VALIDATE_URL = "https://api.nutrient.io/accessibility/validate_pdfua"
PASSWORD_HEADER = "pspdfkit-pdf-password"
MAX_LISTED_OCCURRENCES = 3

EXIT_CONFORMS = 0
EXIT_ERROR = 1
EXIT_NOT_CONFORMANT = 3


# --------------------------------------------------------------------------------------------
# Pure helpers (no network / key) — unit-tested.
# --------------------------------------------------------------------------------------------
def is_conformant(report: dict) -> bool:
    """True only when the API reports the PDF as valid. Missing or malformed fields count as a
    failure, so a truncated or unexpected body can't be read as a pass."""
    return report.get("isValid") is True


def summarize_report(report: dict, name: str) -> str:
    """Plain-language summary of a validate_pdfua report for the agent to relay to the user."""
    vr = report.get("validationReport") or {}
    if is_conformant(report):
        return f"{name} conforms to PDF/UA-1. No failed checks."
    checks = vr.get("failedChecks") or []
    count = vr.get("failureCount")
    if count is None:
        count = sum(c.get("occurrenceCount", 0) or 0 for c in checks)
    lines = [
        f"{name} does not conform to PDF/UA-1: {count} failure(s) across {len(checks)} check(s).",
    ]
    statement = (vr.get("result") or {}).get("statement")
    if statement:
        lines.append(f"Validator: {statement}")
    for check in checks:
        occurrences = check.get("occurrences") or []
        n = check.get("occurrenceCount", len(occurrences))
        first = next((o.get("statement") for o in occurrences if o.get("statement")), None)
        label = first or check.get("id") or "Unnamed check"
        lines.append(f"- {label} ({n} occurrence(s), check {check.get('id', 'unknown')})")
        for occ in occurrences[:MAX_LISTED_OCCURRENCES]:
            where = occ.get("objectReference") or occ.get("context")
            if where:
                lines.append(f"    at {where}")
        if len(occurrences) > MAX_LISTED_OCCURRENCES:
            lines.append(f"    and {len(occurrences) - MAX_LISTED_OCCURRENCES} more")
    return "\n".join(lines)


def password_header_value(password: str) -> str:
    """HTTP header value for a PDF password. Non-ASCII passwords go Base64-encoded as
    `base64:<encoded>`, the form the API documents for characters a header can't carry."""
    if all(32 <= ord(c) < 127 for c in password):
        return password
    import base64

    return "base64:" + base64.b64encode(password.encode("utf-8")).decode("ascii")


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Validate a PDF against PDF/UA-1 via the Nutrient Accessibility API.",
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", help="Local PDF to validate.")
    src.add_argument("--url", help="Remote PDF URL (https only) to validate.")
    p.add_argument("--report", help="Where to write the JSON report. Default: <input-stem>-validation.json.")
    p.add_argument("--password-env", dest="password_env",
                   help="Name of an environment variable holding the PDF's password, if it has one.")
    return p


def _require_key() -> str:
    key = os.environ.get("NUTRIENT_ACCESSIBILITY_API_KEY")
    if not key:
        print(
            "NUTRIENT_ACCESSIBILITY_API_KEY is not set. Export your Nutrient API key before running "
            "this script.",
            file=sys.stderr,
        )
        sys.exit(EXIT_ERROR)
    return key


def _resolve_report(args) -> Path:
    if args.report:
        return Path(args.report)
    if args.input:
        stem = Path(args.input)
        return stem.with_name(f"{stem.stem}-validation.json")
    return Path("validation.json")


async def main() -> None:
    args = build_parser().parse_args()
    key = _require_key()

    try:
        if args.input:
            validate_input(Path(args.input))
        else:
            validate_remote_url(args.url)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    headers = {"Authorization": f"Bearer {key}"}
    if args.password_env:
        password = os.environ.get(args.password_env)
        if not password:
            print(f"Error: environment variable {args.password_env} is not set.", file=sys.stderr)
            sys.exit(EXIT_ERROR)
        headers[PASSWORD_HEADER] = password_header_value(password)

    report_path = _resolve_report(args)
    if report_path.is_symlink() or report_path.is_dir():
        print(f"Error: --report must be a regular file path: {report_path}", file=sys.stderr)
        sys.exit(EXIT_ERROR)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    import httpx

    async with httpx.AsyncClient(timeout=180) as client:
        if args.input:
            file_bytes = Path(args.input).read_bytes()
            file_name = Path(args.input).name
        else:
            # Same client-side fetch as autotag.py: the Nutrient backend never fetches the URL.
            validate_remote_url(args.url)
            buf = bytearray()
            async with client.stream("GET", args.url, follow_redirects=False) as dl:
                if dl.status_code // 100 != 2:
                    print(f"Error: could not fetch --url (HTTP {dl.status_code}); redirects are "
                          "not followed.", file=sys.stderr)
                    sys.exit(EXIT_ERROR)
                async for piece in dl.aiter_bytes():
                    buf += piece
                    if len(buf) > MAX_BYTES:
                        print("Error: --url body exceeds the 150 MiB limit; download aborted.",
                              file=sys.stderr)
                        sys.exit(EXIT_ERROR)
            file_bytes = bytes(buf)
            file_name = Path(urlparse(args.url).path).name or "remote.pdf"

        files = {"file": (file_name, file_bytes, "application/pdf")}
        resp = await client.post(VALIDATE_URL, headers=headers, files=files)

    if resp.status_code // 100 != 2:
        body = redact(resp.text, key)
        hint = {
            401: "The API key is missing or invalid.",
            402: "The account has no usage left for validation this month.",
            403: "The PDF password is missing or incorrect (pass it with --password-env).",
            413: "The file exceeds the maximum upload size.",
        }.get(resp.status_code, "")
        print(f"Error: HTTP {resp.status_code}. {hint}\n{body}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    try:
        report = resp.json()
    except ValueError:
        print("Error: the API returned a non-JSON response.\n" + redact(resp.text[:500], key),
              file=sys.stderr)
        sys.exit(EXIT_ERROR)

    fd = os.open(report_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Wrote {report_path}")
    print(summarize_report(report, file_name))
    sys.exit(EXIT_CONFORMS if is_conformant(report) else EXIT_NOT_CONFORMANT)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(str(e), file=sys.stderr)
        sys.exit(EXIT_ERROR)
