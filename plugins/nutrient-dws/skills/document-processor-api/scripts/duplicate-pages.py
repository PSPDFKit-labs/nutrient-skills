#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["nutrient-dws"]
# ///

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.common import create_client, write_binary_output, parse_integer_csv, handle_error, fix_negative_args


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a new PDF from specific page indices (supports duplicates/reordering).",
        epilog="Example: uv run scripts/duplicate-pages.py --input doc.pdf --pages 2,0,1,1 --out reordered.pdf",
    )
    parser.add_argument("--input", required=True, help="Path or URL to the input PDF.")
    parser.add_argument(
        "--pages", required=True, help="Comma-separated 0-based page indices to include."
    )
    parser.add_argument("--out", required=True, help="Output file path.")
    args = parser.parse_args(fix_negative_args())

    page_indices = parse_integer_csv(args.pages)
    if not page_indices:
        parser.error("--pages must include at least one index.")

    client = create_client()
    result = await client.duplicate_pages(args.input, page_indices)
    write_binary_output(result, args.out)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
