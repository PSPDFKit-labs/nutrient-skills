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
from lib.common import create_client, write_binary_output, parse_csv, parse_page_range, handle_error, fix_negative_args


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split one PDF into multiple PDFs by page ranges.",
        epilog="Example: uv run scripts/split.py --input report.pdf --ranges 0:2,3:5,-2:-1 --out-dir out --prefix section",
    )
    parser.add_argument("--input", required=True, help="Path or URL to the input PDF.")
    parser.add_argument(
        "--ranges", required=True, help="Comma-separated page ranges in start:end format."
    )
    parser.add_argument("--out-dir", dest="out_dir", required=True, help="Output directory.")
    parser.add_argument(
        "--prefix", default="split", help="Filename prefix for output files (default: split)."
    )
    args = parser.parse_args(fix_negative_args())

    ranges_raw = parse_csv(args.ranges)
    if not ranges_raw:
        parser.error("--ranges requires at least one range in start:end format.")
    ranges = [parse_page_range(r) for r in ranges_raw]

    client = create_client()
    results = await client.split(args.input, ranges)

    for i, result in enumerate(results):
        output_path = str(Path(args.out_dir) / f"{args.prefix}-{str(i + 1).zfill(2)}.pdf")
        write_binary_output(result, output_path)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
