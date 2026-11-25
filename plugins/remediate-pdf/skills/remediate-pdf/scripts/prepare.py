#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27", "pypdf>=4.0"]
# ///
"""Prepare a document for auto-tagging: convert it to PDF, run OCR, or both.

Nutrient Accessibility API takes PDF only, and auto-tagging structures the text it finds, so:
- Word, Excel, PowerPoint, text, and image files are converted to PDF first.
- Scanned PDFs (pages with no text layer) and images need OCR first, or auto-tagging tags each page
  as a single figure with no readable text.

Both run through the Nutrient Processor `/build` endpoint with the same API key and plan as the
Accessibility API. Conversion is billed per operation and OCR per page, from the account's monthly
usage, then the wallet. On the free plan, Processor output carries an evaluation watermark, which
auto-tagging would tag as page content.

Exit codes: 0 = prepared PDF written, 1 = error, 2 = cost gate declined.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from autotag import MAX_BYTES, quota_gate, redact  # noqa: E402

BUILD_URL = "https://api.nutrient.io/build"
DEFAULT_CONFIRM_OVER = 20
OFFICE_AND_TEXT = {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pps", ".ppsx",
                   ".rtf", ".odt", ".txt"}
IMAGES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".gif", ".bmp", ".webp", ".heic"}
WATERMARK_NOTE = (
    "Note: on the free plan, converted and OCR'd output carries an evaluation watermark, and "
    "auto-tagging tags it as page content. Use a paid plan or pay-as-you-go for documents you "
    "plan to publish."
)


# --------------------------------------------------------------------------------------------
# Pure helpers (no network / key) — unit-tested.
# --------------------------------------------------------------------------------------------
def classify_input(path: Path) -> str:
    """Return 'pdf', 'office', or 'image'. Raise ValueError for missing, unsupported, or oversized
    files. CSV, Markdown, and HTML are not converted here."""
    if not path.exists():
        raise ValueError(f"input file not found: {path}")
    size = path.stat().st_size
    if size > MAX_BYTES:
        raise ValueError(f"input is {size / 1024 / 1024:.1f} MiB, over the 150 MiB limit.")
    ext = path.suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext in OFFICE_AND_TEXT:
        return "office"
    if ext in IMAGES:
        return "image"
    raise ValueError(
        f"unsupported input type '{ext}'. Supported: PDF, Word, Excel, PowerPoint, RTF, ODT, "
        "text, and image files."
    )


def build_instructions(ocr_languages: list[str] | None) -> dict:
    """Processor /build instructions: the uploaded file as the only part, plus OCR if requested."""
    instructions: dict = {"parts": [{"file": "document"}]}
    if ocr_languages:
        language = ocr_languages[0] if len(ocr_languages) == 1 else ocr_languages
        instructions["actions"] = [{"type": "ocr", "language": language}]
    return instructions


def parse_languages(value: str | None) -> list[str] | None:
    if value is None:
        return None
    langs = [v.strip() for v in value.split(",") if v.strip()]
    if not langs:
        raise ValueError("--ocr needs at least one language, for example --ocr english")
    return langs


def text_layer_status(path: Path, max_pages: int = 3):
    """True if the first pages of a PDF have extractable text, False if none do (likely a scan),
    None if the file can't be read."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        for page in reader.pages[:max_pages]:
            if (page.extract_text() or "").strip():
                return True
        return False
    except Exception:
        return None


def pdf_page_count(path: Path):
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(path)).pages)
    except Exception:
        return None


def default_output(path: Path, ocr: bool) -> Path:
    """<stem>.pdf for a conversion, <stem>-ocr.pdf when OCR runs (so a PDF input is never
    overwritten)."""
    return path.with_name(f"{path.stem}{'-ocr' if ocr else ''}.pdf")


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convert a document to PDF and/or run OCR before auto-tagging.",
        epilog="Examples:\n"
               "  uv run scripts/prepare.py --input report.docx\n"
               "  uv run scripts/prepare.py --input scan.pdf --ocr english\n"
               "  uv run scripts/prepare.py --input photo.jpg --ocr english,german",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--input", required=True, help="Local file to prepare.")
    p.add_argument("--output", help="Output PDF path. Default: <input-stem>.pdf or <input-stem>-ocr.pdf.")
    p.add_argument("--ocr", metavar="LANGUAGES",
                   help="Run OCR in these comma-separated languages, for example english or english,german.")
    p.add_argument("--confirm-over", dest="confirm_over", type=int, default=DEFAULT_CONFIRM_OVER,
                   help="Confirm before OCR on more than this many pages (default 20).")
    p.add_argument("--yes", action="store_true", help="Bypass the cost confirmation gate.")
    return p


def _require_key() -> str:
    key = os.environ.get("NUTRIENT_ACCESSIBILITY_API_KEY") or os.environ.get("NUTRIENT_API_KEY")
    if not key:
        print(
            "Set NUTRIENT_ACCESSIBILITY_API_KEY (or NUTRIENT_API_KEY) to your Nutrient API key. "
            "One account and plan cover the Accessibility API and the Processor API.",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


async def main() -> None:
    args = build_parser().parse_args()
    key = _require_key()
    in_path = Path(args.input)

    try:
        kind = classify_input(in_path)
        languages = parse_languages(args.ocr)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if kind == "pdf" and not languages:
        status = text_layer_status(in_path)
        if status is True:
            print("This PDF already has a text layer; nothing to prepare. Auto-tag it directly.",
                  file=sys.stderr)
        else:
            print("This is already a PDF. If it is a scan, re-run with --ocr <language>.",
                  file=sys.stderr)
        sys.exit(0)

    if languages and kind == "pdf":
        proceed, message = quota_gate(pdf_page_count(in_path), args.confirm_over, args.yes,
                                      sys.stdin.isatty())
        if not proceed:
            print(message.replace("auto-tagging", "OCR").replace("Auto-tagging", "OCR"),
                  file=sys.stderr)
            sys.exit(2)

    out_path = Path(args.output) if args.output else default_output(in_path, bool(languages))
    if out_path.is_symlink() or out_path.is_dir():
        print(f"Error: --output must be a regular file path: {out_path}", file=sys.stderr)
        sys.exit(1)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    import httpx

    files = {
        "document": (in_path.name, in_path.read_bytes(), "application/octet-stream"),
        "instructions": (None, json.dumps(build_instructions(languages)), "application/json"),
    }
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(BUILD_URL, headers={"Authorization": f"Bearer {key}"}, files=files)

    if resp.status_code // 100 != 2:
        print(f"Error: HTTP {resp.status_code}\n{redact(resp.text, key)}", file=sys.stderr)
        sys.exit(1)
    if resp.content[:4] != b"%PDF":
        print("Error: expected a PDF from /build but got something else.", file=sys.stderr)
        sys.exit(1)

    fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(resp.content)
    action = " and ".join(a for a, on in (("converted", kind != "pdf"), ("OCR'd", bool(languages))) if on)
    print(f"Wrote {out_path} ({action}). Next: auto-tag it with scripts/autotag.py.")
    print(WATERMARK_NOTE, file=sys.stderr)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(str(e), file=sys.stderr)
        sys.exit(1)
