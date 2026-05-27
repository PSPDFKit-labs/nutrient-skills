import os
import sys
from typing import NoReturn


def create_client():
    """Create and return a NutrientClient configured for DWS Extract.

    DWS Extract is a separate product from DWS Processor and has its own
    API key. Reads NUTRIENT_EXTRACT_API_KEY (required); falls back to
    NUTRIENT_API_KEY if the former is unset, so a single global key works
    once DWS rolls those out.

    Uses `is None` rather than truthiness so an explicitly empty
    NUTRIENT_EXTRACT_API_KEY (`export NUTRIENT_EXTRACT_API_KEY=`) is treated
    as a misconfiguration to surface, not as "fall back to the other key".
    """
    extract_api_key = os.environ.get("NUTRIENT_EXTRACT_API_KEY")
    fallback_key = os.environ.get("NUTRIENT_API_KEY")
    if extract_api_key is None and fallback_key is None:
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
    primary = extract_api_key if extract_api_key is not None else fallback_key
    return NutrientClient(api_key=primary, extract_api_key=extract_api_key)


def assert_local_file(value: str, arg: str) -> str:
    """Raise if value looks like a URL; otherwise return the path."""
    v = str(value).strip()
    if v.startswith("http://") or v.startswith("https://"):
        raise ValueError(f"--{arg} must be a local file path for this operation.")
    return v


def handle_error(e: Exception) -> NoReturn:
    """Print the error message and exit with code 1."""
    print(str(e), file=sys.stderr)
    sys.exit(1)
