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
from lib.common import create_client, write_json_output, parse_page_range, handle_error, fix_negative_args


async def main() -> None:
    parser = argparse.ArgumentParser(description="Extract table data from a document.")
    parser.add_argument("--input", required=True, help="Path or URL to the input document.")
    parser.add_argument("--out", required=True, help="Output JSON file path.")
    parser.add_argument("--pages", help="Page range in start:end format.")
    args = parser.parse_args(fix_negative_args())

    pages = parse_page_range(args.pages) if args.pages else None

    client = create_client()
    result = await client.extract_table(args.input, pages)
    write_json_output(result, args.out)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
