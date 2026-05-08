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
        description="Delete specific pages from a PDF.",
        epilog="Example: uv run scripts/delete-pages.py --input doc.pdf --pages 0,2,-1 --out doc-without-pages.pdf",
    )
    parser.add_argument("--input", required=True, help="Path or URL to the input PDF.")
    parser.add_argument(
        "--pages", required=True, help="Comma-separated 0-based page indices to delete."
    )
    parser.add_argument("--out", required=True, help="Output file path.")
    args = parser.parse_args(fix_negative_args())

    page_indices = parse_integer_csv(args.pages)
    if not page_indices:
        parser.error("--pages must include at least one index.")

    client = create_client()
    result = await client.delete_pages(args.input, page_indices)
    write_binary_output(result, args.out)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
