import os
import sys
from typing import NoReturn


def resolve_extract_key() -> str:
    """Return the bearer key used by the DWS Data Extraction API."""
    extract_api_key = os.environ.get("NUTRIENT_EXTRACT_API_KEY")
    if extract_api_key is not None:
        if extract_api_key == "":
            raise RuntimeError(
                "NUTRIENT_EXTRACT_API_KEY is set but empty. Export a non-empty "
                "DWS Extract API key before running this skill's scripts."
            )
        return extract_api_key

    fallback_key = os.environ.get("NUTRIENT_API_KEY")
    if fallback_key:
        return fallback_key

    raise RuntimeError(
        "NUTRIENT_EXTRACT_API_KEY is not set. DWS Extract requires its own "
        "API key (separate from the DWS Processor key). Export it before "
        "running this skill's scripts."
    )


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
    # Intentionally fail before importing the SDK when the extract key is empty.
    primary = resolve_extract_key()
    try:
        from nutrient_dws import NutrientClient
    except ImportError as e:
        raise RuntimeError(
            "Unable to import nutrient_dws. Install with: uv add 'nutrient-dws>=3.1.0'\n"
            f"Original error: {e}"
        ) from e
    extract_api_key = os.environ.get("NUTRIENT_EXTRACT_API_KEY")
    return NutrientClient(api_key=primary, extract_api_key=extract_api_key)


def redact(text: str, key) -> str:
    """Replace every occurrence of a bearer key in text."""
    if key and key in text:
        return text.replace(key, "[REDACTED]")
    return text


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
