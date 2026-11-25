#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27"]
# ///
"""Validate a PDF against PDF/UA-1 via the Nutrient Accessibility API.

POSTs to https://api.nutrient.io/accessibility/validate_pdfua (multipart, field `file`) and writes
the JSON validation report to --report. Prints a plain-language summary of every failed check.

A completed validation returns HTTP 200 whether or not the PDF passes, so the result comes from
`isValid` in the body, not the status code. The API checks the machine-testable PDF/UA-1
requirements; a pass still needs a person to check alt text, reading order, and tag semantics.
Exit codes: 0 = passed machine validation, 3 = failed (report written), 1 = error (nothing
validated).

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
from autotag import (  # noqa: E402
    check_output_path,
    fetch_remote_pdf,
    redact,
    require_key,
    secrets_from_env,
    validate_input,
    validate_remote_url,
    write_private,
)

VALIDATE_URL = "https://api.nutrient.io/accessibility/validate_pdfua"
PASSWORD_HEADER = "pspdfkit-pdf-password"
PASSWORD_ENV = "NUTRIENT_PDF_PASSWORD"
MAX_LISTED_OCCURRENCES = 3

EXIT_PASSED = 0
EXIT_ERROR = 1
EXIT_FAILED = 3

HUMAN_CHECKS = ("A person still needs to check that alt text describes each image, that the "
                "reading order is logical, and that tag types and heading levels are right.")


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
        return f"{name} passed PDF/UA-1 machine validation (no failed checks). {HUMAN_CHECKS}"
    checks = vr.get("failedChecks") or []
    count = vr.get("failureCount")
    if count is None:
        count = sum(c.get("occurrenceCount", 0) or 0 for c in checks)
    lines = [
        f"{name} failed PDF/UA-1 validation: {count} failure(s) across {len(checks)} check(s).",
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
            # Document-level failures carry a placeholder reference ("None" or "0 obj"); the
            # context ("Document", "Page") says more there.
            ref = occ.get("objectReference")
            where = ref if ref and ref not in ("None", "0 obj") else occ.get("context")
            if where:
                lines.append(f"    at {where}")
        if len(occurrences) > MAX_LISTED_OCCURRENCES:
            lines.append(f"    and {len(occurrences) - MAX_LISTED_OCCURRENCES} more")
    return "\n".join(lines)


def password_header_value(password: str) -> str:
    """HTTP header value for a PDF password, always as `base64:<encoded>`, the form the API
    documents. Encoding every password means spaces, non-ASCII, or a literal `base64:` prefix
    can't break the header or make the HTTP library echo the password in an error."""
    import base64

    return "base64:" + base64.b64encode(password.encode("utf-8")).decode("ascii")


def error_hint(status: int, sent_password: bool) -> str:
    """Plain-language hint for an API error status."""
    if status == 403:
        if sent_password:
            return ("The PDF password is incorrect, or the key isn't enabled for the "
                    "Accessibility API.")
        return (f"The PDF may be password-protected: export {PASSWORD_ENV} and pass "
                "--with-password. Otherwise the key isn't enabled for the Accessibility API.")
    return {
        401: "The API key is missing or invalid. Accounts created before the unified plan "
             "(16 Nov 2026) may have separate keys per API; check the dashboard.",
        402: "The account's usage is used up. Add funds to the wallet or wait for the reset.",
        413: "The file exceeds the maximum upload size.",
    }.get(status, "")


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
    p.add_argument("--report",
                   help="Where to write the JSON report. Default: <input-stem>-validation.json.")
    p.add_argument("--overwrite", action="store_true", help="Replace --report if it exists.")
    p.add_argument("--with-password", dest="with_password", action="store_true",
                   help=f"Send the PDF password from the {PASSWORD_ENV} environment variable.")
    return p


def _resolve_report(args) -> Path:
    if args.report:
        return Path(args.report)
    if args.input:
        stem = Path(args.input)
        return stem.with_name(f"{stem.stem}-validation.json")
    return Path(f"{Path(urlparse(args.url).path).stem or 'remote'}-validation.json")


async def main() -> None:
    args = build_parser().parse_args()
    key = require_key()

    in_path = Path(args.input) if args.input else None
    try:
        if in_path:
            validate_input(in_path)
        else:
            validate_remote_url(args.url)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    headers = {"Authorization": f"Bearer {key}"}
    password = None
    if args.with_password:
        password = os.environ.get(PASSWORD_ENV)
        if not password:
            print(f"Error: {PASSWORD_ENV} is not set.", file=sys.stderr)
            sys.exit(EXIT_ERROR)
        headers[PASSWORD_HEADER] = password_header_value(password)

    # Preflight the report target before the billable POST.
    report_path = _resolve_report(args)
    try:
        check_output_path(report_path, in_path, args.overwrite)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    import httpx

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
        resp = await client.post(VALIDATE_URL, headers=headers, files=files)

    if resp.status_code // 100 != 2:
        body = redact(resp.text, key, password)
        hint = error_hint(resp.status_code, password is not None)
        print(f"Error: HTTP {resp.status_code}. {hint}\n{body}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    try:
        report = resp.json()
    except ValueError:
        print("Error: the API returned a non-JSON response.\n"
              + redact(resp.text[:500], key, password), file=sys.stderr)
        sys.exit(EXIT_ERROR)

    write_private(report_path, json.dumps(report, indent=2).encode("utf-8"), args.overwrite)
    print(f"Wrote {report_path}")
    print(summarize_report(report, file_name))
    sys.exit(EXIT_PASSED if is_conformant(report) else EXIT_FAILED)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"Error: {redact(str(e), *secrets_from_env())}", file=sys.stderr)
        sys.exit(EXIT_ERROR)
