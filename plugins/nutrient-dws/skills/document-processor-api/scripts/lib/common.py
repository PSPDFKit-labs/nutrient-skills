import json
import os
import re
import sys
from pathlib import Path
from typing import Any, NoReturn

_NEGATIVE_VALUE_RE = re.compile(r"^-\d")


def create_client():
    """Create and return a NutrientClient using the NUTRIENT_API_KEY env var."""
    api_key = os.environ.get("NUTRIENT_API_KEY")
    if not api_key:
        raise RuntimeError(
            "NUTRIENT_API_KEY is not set. Export it before running these scripts."
        )
    try:
        from nutrient_dws import NutrientClient
    except ImportError as e:
        raise RuntimeError(
            "Unable to import nutrient_dws. Install with: uv add nutrient-dws\n"
            f"Original error: {e}"
        ) from e
    return NutrientClient(api_key=api_key)


def write_binary_output(result: dict, path: str) -> None:
    """Write a BufferOutput result to disk."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(result["buffer"])
    mime = result.get("mimeType", "application/octet-stream")
    print(f"Wrote {path} ({mime})")


def write_json_output(result: dict, path: str) -> None:
    """Write a JsonContentOutput result to disk (only the data portion)."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result["data"], f, indent=2)
    print(f"Wrote {path}")


def write_workflow_output(result: dict, path: str) -> None:
    """Write a WorkflowResult to disk, raising on failure."""
    if not result.get("success") or not result.get("output"):
        errors = result.get("errors") or []
        msgs = "; ".join(
            str(e.get("error", e)) for e in errors
        )
        raise RuntimeError(f"Workflow failed: {msgs or 'unknown error'}")
    write_binary_output(result["output"], path)


def parse_page_range(value: str) -> dict:
    """Parse 'start:end' into {'start': int, 'end': int}."""
    parts = str(value).split(":")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid page range '{value}'. Use start:end (e.g. 0:4 or -3:-1)."
        )
    result = {}
    if parts[0] != "":
        try:
            result["start"] = int(parts[0])
        except ValueError:
            raise ValueError(f"Invalid start in page range '{value}'.")
    if parts[1] != "":
        try:
            result["end"] = int(parts[1])
        except ValueError:
            raise ValueError(f"Invalid end in page range '{value}'.")
    if not result:
        raise ValueError(
            f"Invalid page range '{value}'. Use start:end (e.g. 0:4 or -3:-1)."
        )
    return result


def parse_csv(value: str) -> list[str]:
    """Split a comma-separated string into a list of trimmed, non-empty strings."""
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def parse_integer_csv(value: str) -> list[int]:
    """Split a comma-separated string into a list of integers."""
    result = []
    for item in parse_csv(value):
        try:
            result.append(int(item))
        except ValueError:
            raise ValueError(f"Invalid integer value: '{item}'")
    return result


def assert_local_file(value: str, arg: str) -> str:
    """Raise if value looks like a URL; otherwise return the path."""
    v = str(value).strip()
    if v.startswith("http://") or v.startswith("https://"):
        raise ValueError(f"--{arg} must be a local file path for this operation.")
    return v


def read_json_file(path: str) -> Any:
    """Read and parse a JSON file."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file ({path}): {e}") from e


def parse_json_string(s: str) -> Any:
    """Parse a JSON string."""
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON string: {e}") from e


def fix_negative_args() -> list[str]:
    """Return sys.argv[1:] with negative numeric values joined to their flag.

    argparse treats values like ``-1`` or ``-1:3`` as unknown option flags when
    passed as a separate token. This helper reattaches them using ``=`` so that
    ``--pages -1`` becomes ``--pages=-1`` before argparse sees the arguments.
    """
    argv = sys.argv[1:]
    result = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if (
            arg.startswith("--")
            and "=" not in arg
            and i + 1 < len(argv)
            and _NEGATIVE_VALUE_RE.match(argv[i + 1])
        ):
            result.append(f"{arg}={argv[i + 1]}")
            i += 2
        else:
            result.append(arg)
            i += 1
    return result


def handle_error(e: Exception) -> NoReturn:
    """Print the error message and exit with code 1."""
    print(str(e), file=sys.stderr)
    sys.exit(1)
