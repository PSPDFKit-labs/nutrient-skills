#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["nutrient-dws>=3.1.0"]
# ///
"""Parse a document using the Nutrient Data Extraction API (/extraction/parse).

This script is the single primitive for document understanding via /extraction/parse.
One call returns the full structural document model — typed elements with bounding boxes,
confidence scores, and reading order — or a whole-document Markdown string.

DWS Extract is a separate product from DWS Processor. It uses its own API key, supplied
via the NUTRIENT_EXTRACT_API_KEY environment variable. Calls to /extraction/parse with a
DWS Processor key return 403.

Billing note: /extraction/parse is billed against **extraction credits**, which are a
separate billing bucket from the processor API credits consumed by /build, /sign, OCR,
and other Processor API endpoints.

Per-page extraction-credit costs by mode:
  text:       1 extraction credit  — fast Markdown from born-digital documents (no OCR/AI)
  structure:  1.5 extraction credits — OCR + spatial elements with bounding boxes
  understand: 9 extraction credits  — AI layout analysis, table detection, semantic classification
  agentic:    18 extraction credits — VLM-augmented; deepest visual understanding

Output shapes:
  spatial  (default): response.output.elements — typed elements list
  markdown:           response.output.markdown — whole-document Markdown string

Usage examples:
  # Spatial elements (structure mode) — lowest-cost spatial extraction
  uv run scripts/parse.py --input doc.pdf --out out.json

  # Markdown for RAG / search indexing (text mode — cheapest)
  uv run scripts/parse.py --input doc.pdf --out out.md --output-format markdown --mode text

  # Form / invoice extraction (understand mode — typed elements with confidence)
  uv run scripts/parse.py --input doc.pdf --out out.json --mode understand

  # Deep visual understanding (agentic mode — VLM descriptions on pictures)
  uv run scripts/parse.py --input doc.pdf --out out.json --mode agentic --output-format spatial
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.common import create_client, handle_error


async def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Parse a document with the Nutrient Data Extraction API and write the result. "
            "Billed against extraction credits (separate from processor API credits)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Extraction credit costs per page:
  text:       1 extraction credit  (born-digital Markdown, no OCR)
  structure:  1.5 extraction credits (OCR + spatial elements)  [default]
  understand: 9 extraction credits  (AI layout + table detection)
  agentic:    18 extraction credits (VLM-augmented)

Output shapes:
  spatial  (default): typed element list at output.elements
  markdown:           whole-document Markdown at output.markdown
""",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the local input document (PDF, image, or Office file).",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output file path. Receives the full JSON response for spatial output, "
        "or a .md file for markdown output.",
    )
    parser.add_argument(
        "--mode",
        choices=["text", "structure", "understand", "agentic"],
        default="structure",
        help=(
            "Processing mode controlling cost and quality. "
            "text=1cr, structure=1.5cr (default), understand=9cr, agentic=18cr — "
            "all costs are extraction credits per page."
        ),
    )
    parser.add_argument(
        "--output-format",
        dest="output_format",
        choices=["spatial", "markdown"],
        default="spatial",
        help=(
            "Shape of the output. "
            "spatial: typed elements with bounds (default). "
            "markdown: whole-document Markdown string."
        ),
    )
    args = parser.parse_args()

    # Validate input is a local file (the /extraction/parse endpoint is multipart-only)
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    client = create_client()
    response = await client.parse(
        input_path,
        mode=args.mode,
        output_format=args.output_format,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.output_format == "markdown":
        markdown = response.get("output", {}).get("markdown", "")
        out_path.write_text(markdown, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(response, f, indent=2)
        print(f"Wrote {args.out}")

    # Print usage summary so callers can see credit cost without opening the output file
    usage = response.get("usage", {})
    credits_info = usage.get("data_extraction_credits", {})
    cost = credits_info.get("cost")
    remaining = credits_info.get("remainingCredits")
    metrics = response.get("metrics", {})
    pages = metrics.get("pagesProcessed", "?")
    if cost is not None:
        remaining_str = f", remaining: {remaining}" if remaining is not None else ""
        print(
            f"Usage: {cost} extraction credits ({pages} page(s) at {args.mode} mode"
            f"{remaining_str})"
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
