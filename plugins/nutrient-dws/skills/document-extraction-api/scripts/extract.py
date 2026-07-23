#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27", "pypdf>=4.0"]
# ///
"""Extract schema-defined fields with the Nutrient Data Extraction API."""

import argparse
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from lib.common import assert_local_file, handle_error, redact, resolve_extract_key


EXTRACT_URL = "https://api.nutrient.io/extraction/extract"
EXTRACT_MODE_COST = {
    "text": 7,
    "structure": 7.5,
    "understand": 15,
    "agentic": 24,
}
COST_GATE_CREDITS = 200
MAX_SCHEMA_BYTES = 32 * 1024
MAX_INSTRUCTIONS = 10_000
HTTP_TIMEOUT = 300.0


def _reject_non_finite(value):
    """Reject NaN/Infinity, which Python's json accepts but standard JSON does not."""
    raise ValueError(f"Schema contains a non-standard JSON constant: {value}")


def load_schema(path) -> dict:
    """Load a JSON Schema from disk, rejecting non-standard constants (NaN/Infinity)."""
    return json.loads(
        Path(path).read_text(encoding="utf-8"), parse_constant=_reject_non_finite
    )


def validate_schema(schema, instructions) -> None:
    """Validate the unambiguous client-side extraction limits."""
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise ValueError("Schema root must be a JSON object with type 'object'.")

    # Measure the same bytes the multipart body sends (ensure_ascii=False, UTF-8), so a
    # valid non-ASCII schema isn't rejected for its escaped-ASCII size.
    schema_bytes = len(json.dumps(schema, ensure_ascii=False).encode("utf-8"))
    if schema_bytes > MAX_SCHEMA_BYTES:
        raise ValueError(
            f"Schema exceeds the {MAX_SCHEMA_BYTES}-byte serialized JSON limit."
        )

    if instructions and len(instructions) > MAX_INSTRUCTIONS:
        raise ValueError(
            f"Instructions exceed the {MAX_INSTRUCTIONS}-character limit."
        )


def build_instructions(
    schema,
    instructions,
    mode,
    include_citations,
    store_run,
) -> dict:
    """Build the extraction instruction fields without reordering the schema."""
    result = {
        "schema": schema,
        "parseConfig": {"mode": mode},
        "options": {"includeCitations": include_citations},
    }
    if instructions:
        result["instructions"] = instructions
    if store_run:
        result["storeRun"] = True
    return result


def estimate_cost(pages, mode) -> float | None:
    """Estimate combined parse and extraction credits."""
    if pages is None:
        return None
    return float(pages * EXTRACT_MODE_COST[mode])


def preflight(pages, mode, yes) -> tuple[bool, str]:
    """Decide whether the estimated extraction cost may proceed."""
    estimate = estimate_cost(pages, mode)
    if estimate is None:
        # Unknown page count (URL input or a non-PDF): proceed, but --yes silences the note.
        if yes:
            return True, ""
        return (
            True,
            "Warning: page count is unknown; extraction cost cannot be pre-estimated. "
            "Re-run with --yes to silence this.",
        )
    if estimate > COST_GATE_CREDITS and not yes:
        return (
            False,
            f"Estimated extraction cost is {estimate:g} credits, above the "
            f"{COST_GATE_CREDITS}-credit safety gate. Re-run with --yes to proceed.",
        )
    return True, ""


def summarize_response(response) -> str:
    """Summarize only top-level data and overall citation presence."""
    output = response.get("output") if isinstance(response, dict) else None
    output = output if isinstance(output, dict) else {}
    data = output.get("data")
    metadata = output.get("metadata") or {}
    keys = list(data) if isinstance(data, dict) else []
    key_summary = ", ".join(str(key) for key in keys) if keys else "(none)"
    citation_summary = "present" if isinstance(metadata, (dict, list)) and metadata else "none"
    return f"Extracted top-level fields: {key_summary}\ncitations: {citation_summary}"


def _local_page_count(path) -> int | None:
    """Return a local PDF's page count when it can be determined safely."""
    input_path = Path(path)
    if input_path.suffix.lower() != ".pdf":
        return None
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(input_path)).pages)
    except Exception:
        return None


def _post(url: str, **kwargs):
    """Small request seam for keyless network tests."""
    return httpx.post(url, **kwargs)


def _is_writable(path: Path) -> bool:
    """Check both effective access and permission bits for predictable preflight."""
    try:
        mode = path.stat().st_mode
    except OSError:
        return False
    write_bits = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
    return bool(mode & write_bits) and os.access(path, os.W_OK)


def _prepare_output(out_path: Path, protected=()) -> None:
    """Create and validate the output parent before a billed request.

    `protected` are input/schema paths that --out must not alias (same file or hard link):
    the O_TRUNC write would otherwise destroy the source after a paid call.
    """
    for src in protected:
        if src is None:
            continue
        src_path = Path(src)
        try:
            if out_path.exists() and src_path.exists() and out_path.samefile(src_path):
                print(
                    f"Error: --out must not be the same file as {src_path} "
                    "(the write would destroy the source).",
                    file=sys.stderr,
                )
                raise SystemExit(1)
        except OSError:
            pass

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error: unable to create --out parent: {e}", file=sys.stderr)
        raise SystemExit(1) from e

    if out_path.is_symlink():
        print(
            f"Error: refusing to follow symlink for --out: {out_path}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if out_path.is_dir():
        print(
            f"Error: --out must be a file, not a directory: {out_path}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if not _is_writable(out_path.parent):
        print(
            f"Error: --out parent is not writable: {out_path.parent}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if out_path.exists() and not _is_writable(out_path):
        print(f"Error: --out is not writable: {out_path}", file=sys.stderr)
        raise SystemExit(1)


def _safe_write_json(out_path: Path, response: dict) -> None:
    """Atomically write sensitive extraction output at 0600 without following symlinks.

    Write a 0600 temp sibling, fsync, then os.replace onto the target — so a disk-full or
    interrupt after the billed call can't leave a partial file or destroy a prior good output.
    """
    data = json.dumps(response, indent=2)
    # mkstemp creates a UNIQUE file with O_CREAT|O_EXCL at 0600 in the target dir — so a
    # pre-planted hard link can't be truncated (no O_TRUNC on an existing name) and concurrent
    # runs can't share a temp inode. Then fsync + atomic os.replace onto the final name.
    fd, tmp_name = tempfile.mkstemp(dir=str(out_path.parent), prefix=f".{out_path.name}.", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            os.fchmod(f.fileno(), 0o600)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, out_path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _response_failure(message: str, response: httpx.Response, key: str) -> None:
    print(message, file=sys.stderr)
    body = redact(response.text, key)
    if body:
        print(body, file=sys.stderr)
    raise SystemExit(1)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract schema-defined fields with citations using the Nutrient "
            "Data Extraction API."
        )
    )
    parser.add_argument("--input", help="Path to a local input document.")
    parser.add_argument("--url", help="Public URL of the input document.")
    parser.add_argument("--schema", required=True, help="Path to a JSON Schema file.")
    parser.add_argument("--out", required=True, help="Path for the full JSON response.")
    parser.add_argument("--instructions", help="Optional extraction instructions.")
    parser.add_argument(
        "--mode",
        choices=["text", "structure", "understand", "agentic"],
        default="understand",
        help="Parse mode used before field extraction (default: understand).",
    )
    parser.add_argument(
        "--no-citations",
        action="store_true",
        help="Disable citation metadata in the extraction response.",
    )
    parser.add_argument(
        "--store-run",
        action="store_true",
        help="Store the extraction run on the server.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Proceed when the estimated cost exceeds the safety gate.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)

    if bool(args.input) == bool(args.url):
        print(
            "Error: exactly one of --input or --url is required.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    input_path = None
    if args.input:
        input_path = Path(assert_local_file(args.input, "input"))
        if not input_path.exists():
            print(f"Error: input file not found: {args.input}", file=sys.stderr)
            raise SystemExit(1)

    schema = load_schema(args.schema)
    validate_schema(schema, args.instructions)

    out_path = Path(args.out)
    _prepare_output(out_path, protected=[input_path, Path(args.schema)])

    pages = _local_page_count(input_path) if input_path is not None else None
    ok, message = preflight(pages, args.mode, args.yes)
    if message:
        print(message, file=sys.stderr)
    if not ok:
        raise SystemExit(2)

    key = resolve_extract_key()
    instructions = build_instructions(
        schema,
        args.instructions,
        args.mode,
        not args.no_citations,
        args.store_run,
    )
    instructions_json = json.dumps(
        instructions,
        ensure_ascii=False,
        sort_keys=False,
    )
    auth_headers = {"Authorization": f"Bearer {key}"}

    try:
        response = _send(input_path, args, instructions, instructions_json, auth_headers)
    except Exception as e:  # noqa: BLE001 — never let the key leak via an httpx/transport error
        print(f"Error: extraction request failed: {redact(str(e), key)}", file=sys.stderr)
        raise SystemExit(1) from None

    if response.status_code // 100 != 2:
        _response_failure(
            f"Error: extraction request failed with HTTP {response.status_code}.",
            response,
            key,
        )

    try:
        parsed = response.json()
    except ValueError:
        _response_failure(
            "Error: extraction response was not valid JSON.",
            response,
            key,
        )

    # A present-but-non-dict output (e.g. {"output": null}) is malformed, not an empty doc.
    if not isinstance(parsed, dict) or not isinstance(parsed.get("output"), dict):
        _response_failure(
            "Error: extraction response is missing a valid 'output' object.",
            response,
            key,
        )

    _safe_write_json(out_path, parsed)
    print(summarize_response(parsed))

    credits_info = (
        parsed.get("usage", {}).get("data_extraction_credits", {})
        if isinstance(parsed.get("usage", {}), dict)
        else {}
    )
    cost = credits_info.get("cost") if isinstance(credits_info, dict) else None
    remaining = (
        credits_info.get("remainingCredits")
        if isinstance(credits_info, dict)
        else None
    )
    if cost is not None:
        remaining_text = (
            f", remaining: {remaining}" if remaining is not None else ""
        )
        print(f"Usage: {cost} extraction credits{remaining_text}")


def _send(input_path, args, instructions, instructions_json, auth_headers):
    """Issue the extract request: multipart for a local file, JSON body for a URL."""
    if input_path is not None:
        return _post(
            EXTRACT_URL,
            headers=auth_headers,
            files={"file": (input_path.name, input_path.read_bytes())},
            data={"instructions": instructions_json},
            timeout=HTTP_TIMEOUT,
        )
    json_body: dict[str, Any] = {"url": args.url}
    json_body.update(instructions)
    return _post(
        EXTRACT_URL,
        headers={**auth_headers, "Content-Type": "application/json"},
        json=json_body,
        timeout=HTTP_TIMEOUT,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        handle_error(e)
