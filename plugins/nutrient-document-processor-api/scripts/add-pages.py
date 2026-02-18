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
from lib.common import create_client, write_binary_output, handle_error, fix_negative_args


async def main() -> None:
    parser = argparse.ArgumentParser(description="Add blank pages to a PDF.")
    parser.add_argument("--input", required=True, help="Path or URL to the input PDF.")
    parser.add_argument(
        "--count", required=True, type=int, help="Number of blank pages to add."
    )
    parser.add_argument("--out", required=True, help="Output file path.")
    parser.add_argument("--index", type=int, help="Insertion index (0-based; default: end).")
    args = parser.parse_args(fix_negative_args())

    if args.count <= 0:
        parser.error("--count must be a positive integer.")

    client = create_client()
    result = await client.add_page(args.input, args.count, args.index)
    write_binary_output(result, args.out)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
