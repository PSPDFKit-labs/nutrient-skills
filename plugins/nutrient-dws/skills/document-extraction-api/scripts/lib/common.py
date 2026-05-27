import json
import os
import re
import sys
from pathlib import Path
from typing import Any, NoReturn

_NEGATIVE_VALUE_RE = re.compile(r"^-\d")


def create_client():
    """Create and return a NutrientClient configured for DWS Extract.

    DWS Extract is a separate product from DWS Processor and has its own
    API key. Reads NUTRIENT_EXTRACT_API_KEY (required); falls back to
    NUTRIENT_API_KEY if the former is unset, so a single global key works
    once DWS rolls those out.
    """
    extract_api_key = os.environ.get("NUTRIENT_EXTRACT_API_KEY")
    fallback_key = os.environ.get("NUTRIENT_API_KEY")
    if not extract_api_key and not fallback_key:
        raise RuntimeError(
            "NUTRIENT_EXTRACT_API_KEY is not set. DWS Extract requires its own "
            "API key (separate from the DWS Processor key). Export it before "
            "running this skill's scripts."
        )
    try:
        from nutrient_dws import NutrientClient
    except ImportError as e:
        raise RuntimeError(
            "Unable to import nutrient_dws. Install with: uv add 'nutrient-dws>=3.1.0'\n"
            f"Original error: {e}"
        ) from e
    # api_key is required by the constructor; parse() will swap to
    # extract_api_key when set. Pass the Extract key through both so the
    # client works whether or not it's also a global key.
    primary = extract_api_key or fallback_key
    return NutrientClient(api_key=primary, extract_api_key=extract_api_key)


def write_json_output(result: dict, path: str) -> None:
    """Write a JSON-serialisable result to disk."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Wrote {path}")


def parse_csv(value: str) -> list[str]:
    """Split a comma-separated string into a list of trimmed, non-empty strings."""
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


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
