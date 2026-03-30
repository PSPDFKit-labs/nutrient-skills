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
from lib.common import create_client, write_binary_output, handle_error


async def main() -> None:
    parser = argparse.ArgumentParser(description="Merge multiple documents into one PDF.")
    parser.add_argument(
        "--inputs",
        required=True,
        help="Comma-separated list of input file paths or URLs (at least 2).",
    )
    parser.add_argument("--out", required=True, help="Output file path.")
    args = parser.parse_args()

    inputs = [f.strip() for f in args.inputs.split(",") if f.strip()]
    if len(inputs) < 2:
        parser.error("--inputs must contain at least 2 files.")

    client = create_client()
    result = await client.merge(inputs)
    write_binary_output(result, args.out)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
