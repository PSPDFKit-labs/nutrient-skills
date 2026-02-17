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
from lib.common import create_client, write_binary_output, read_json_file, parse_json_string, handle_error


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Optimize PDF size and quality.",
        epilog="Example: uv run scripts/optimize.py --input large.pdf --out optimized.pdf --options-json '{\"mrcCompression\":true}'",
    )
    parser.add_argument("--input", required=True, help="Path or URL to the input PDF.")
    parser.add_argument("--out", required=True, help="Output file path.")
    parser.add_argument(
        "--options-json-file",
        dest="options_json_file",
        help="Path to JSON file with optimization options.",
    )
    parser.add_argument(
        "--options-json", dest="options_json", help="JSON string with optimization options."
    )
    args = parser.parse_args()

    options = None
    if args.options_json_file:
        options = read_json_file(args.options_json_file)
    if args.options_json:
        options = parse_json_string(args.options_json)

    client = create_client()
    result = await client.optimize(args.input, options)
    write_binary_output(result, args.out)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
