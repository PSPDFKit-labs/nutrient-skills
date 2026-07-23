#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27"]
# ///
"""Manage stored processors for the Nutrient Data Extraction API."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from lib.common import redact, resolve_extract_key


BASE_URL = "https://api.nutrient.io"
PROCESSORS_PATH = "/extraction/processors"
HTTP_TIMEOUT = 300.0
KNOWN_NOT_FOUND_CODES = {"processor_not_found", "version_not_found"}
FEATURE_MAY_BE_OFF_MESSAGE = (
    "the data_extraction_processors feature may not be enabled for this tenant — "
    "contact Nutrient to enable it."
)


def _request(method: str, path: str, **kwargs):
    """Small request seam for keyless network tests."""
    return httpx.request(method, f"{BASE_URL}{path}", **kwargs)


def _load_config(path: str) -> Any:
    """Load a processor configuration from a JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage stored Nutrient Data Extraction processors."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List stored processors.")

    create = subparsers.add_parser(
        "create", help="Create a processor and its first version."
    )
    create.add_argument("--name", required=True, help="Processor name (required).")
    create.add_argument(
        "--kind",
        required=True,
        choices=["extract", "parse"],
        help="Processor kind — the endpoint it runs against (required).",
    )
    create.add_argument(
        "--config",
        required=True,
        help="Path to the processor configuration JSON.",
    )
    create.add_argument(
        "--publish",
        action="store_true",
        help="Publish the initial version when creating the processor.",
    )

    show = subparsers.add_parser("show", help="Show a processor and version summary.")
    show.add_argument("--processor", required=True, help="Processor public ID.")

    rename = subparsers.add_parser("rename", help="Rename a processor.")
    rename.add_argument("--processor", required=True, help="Processor public ID.")
    rename.add_argument("--name", required=True, help="New processor name.")

    delete = subparsers.add_parser("delete", help="Soft-delete a processor.")
    delete.add_argument("--processor", required=True, help="Processor public ID.")

    create_version = subparsers.add_parser(
        "create-version", help="Create the next processor version."
    )
    create_version.add_argument(
        "--processor", required=True, help="Processor public ID."
    )
    create_version.add_argument(
        "--config",
        required=True,
        help="Path to the processor configuration JSON.",
    )

    show_version = subparsers.add_parser(
        "show-version", help="Show one processor version and its configuration."
    )
    show_version.add_argument(
        "--processor", required=True, help="Processor public ID."
    )
    show_version.add_argument(
        "--version", required=True, type=int, help="Processor version number."
    )

    publish_version = subparsers.add_parser(
        "publish-version", help="Publish a processor version."
    )
    publish_version.add_argument(
        "--processor", required=True, help="Processor public ID."
    )
    publish_version.add_argument(
        "--version", required=True, type=int, help="Processor version number."
    )

    return parser


def _processor_path(public_id: str) -> str:
    return f"{PROCESSORS_PATH}/{quote(public_id, safe='')}"


def _operation(args: argparse.Namespace) -> tuple[str, str, dict[str, Any]]:
    """Translate a parsed subcommand into its HTTP method, path, and kwargs."""
    if args.command == "list":
        return "GET", PROCESSORS_PATH, {}

    if args.command == "create":
        # The server requires both name and kind; config defaults to {} server-side
        # but we always send the supplied config.
        body: dict[str, Any] = {
            "name": args.name,
            "kind": args.kind,
            "config": _load_config(args.config),
        }
        if args.publish:
            body["publish"] = True
        return "POST", PROCESSORS_PATH, {"json": body}

    processor_path = _processor_path(args.processor)
    if args.command == "show":
        return "GET", processor_path, {}
    if args.command == "rename":
        return "PATCH", processor_path, {"json": {"name": args.name}}
    if args.command == "delete":
        return "DELETE", processor_path, {}
    if args.command == "create-version":
        return (
            "POST",
            f"{processor_path}/versions",
            {"json": {"config": _load_config(args.config)}},
        )
    if args.command == "show-version":
        return "GET", f"{processor_path}/versions/{args.version}", {}
    if args.command == "publish-version":
        return "POST", f"{processor_path}/versions/{args.version}/publish", {}

    raise ValueError(f"Unsupported command: {args.command}")


def _response_payload(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def _error_code(payload: Any) -> str | None:
    """Extract an error code from the DWS error envelope.

    DWS errors carry the code at top-level ``errorCode`` and, redundantly, at
    ``errorDetails.code`` (see the hosted ProcessorController). Simpler
    ``code`` / ``error.code`` shapes are tolerated as a fallback.
    """
    if not isinstance(payload, dict):
        return None

    code = payload.get("errorCode")
    if isinstance(code, str):
        return code

    details = payload.get("errorDetails")
    if isinstance(details, dict) and isinstance(details.get("code"), str):
        return details["code"]

    code = payload.get("code")
    if isinstance(code, str):
        return code

    error = payload.get("error")
    if isinstance(error, dict) and isinstance(error.get("code"), str):
        return error["code"]
    if isinstance(error, str) and error in KNOWN_NOT_FOUND_CODES:
        return error
    return None


def _error_detail(response: httpx.Response, payload: Any) -> str:
    if isinstance(payload, dict):
        # DWS uses "errorMessage"; tolerate a plain "message" or nested "error.message".
        for candidate in (payload.get("errorMessage"), payload.get("message")):
            if isinstance(candidate, str) and candidate:
                return candidate
        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str) and error["message"]:
            return error["message"]
        return json.dumps(payload, ensure_ascii=False)
    return response.text


def _fail_for_response(response: httpx.Response, key: str) -> None:
    payload = _response_payload(response)
    code = _error_code(payload)
    detail = redact(_error_detail(response, payload), key)

    if code in KNOWN_NOT_FOUND_CODES:
        message = f"Error: {code} (HTTP {response.status_code})"
        if detail:
            message += f": {detail}"
    elif response.status_code == 409:
        message = "Error: processor name collision (HTTP 409)"
        if detail:
            message += f": {detail}"
    elif response.status_code in {403, 404} and code is None:
        # Only an UNCODED 403/404 is the feature-gate signal (EnforceFeatures returns a bare
        # 404 before the controller). A coded 403/404 (access_denied, route_not_found, …) is a
        # real error and keeps its own code below — never mislabeled "feature off".
        message = FEATURE_MAY_BE_OFF_MESSAGE
    else:
        message = f"Error: processor request failed with HTTP {response.status_code}"
        if code:
            message += f" ({code})"
        if detail:
            message += f": {detail}"

    print(redact(message, key), file=sys.stderr)
    raise SystemExit(1)


def _print_success(response: httpx.Response, method: str, path: str, key: str | None) -> None:
    payload = _response_payload(response)
    if payload is None:
        print(f"{method} {path} succeeded (HTTP {response.status_code}).")
        return
    # Redact the key even from success output — defensive, consistent with every other path.
    print(redact(json.dumps(payload, indent=2, ensure_ascii=False), key))


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    key: str | None = None

    try:
        method, path, request_kwargs = _operation(args)
        key = resolve_extract_key()
        response = _request(
            method,
            path,
            headers={"Authorization": f"Bearer {key}"},
            timeout=HTTP_TIMEOUT,
            **request_kwargs,
        )
    except Exception as exc:  # noqa: BLE001 — redact all request/config error output
        print(
            f"Error: processor request failed: {redact(str(exc), key)}",
            file=sys.stderr,
        )
        raise SystemExit(1) from None

    if response.status_code // 100 != 2:
        _fail_for_response(response, key)

    _print_success(response, method, path, key)


if __name__ == "__main__":
    main()
