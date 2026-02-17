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
    parser = argparse.ArgumentParser(description="Add a text watermark to a document.")
    parser.add_argument("--input", required=True, help="Path or URL to the input document.")
    parser.add_argument("--text", required=True, help="Watermark text.")
    parser.add_argument("--out", required=True, help="Output file path.")
    parser.add_argument("--opacity", type=float, help="Watermark opacity (0.0–1.0).")
    parser.add_argument("--font-size", dest="font_size", type=int, help="Font size in points.")
    parser.add_argument("--rotation", type=int, help="Rotation angle in degrees (integer).")
    args = parser.parse_args()

    options: dict = {}
    if args.opacity is not None:
        options["opacity"] = args.opacity
    if args.font_size is not None:
        options["fontSize"] = args.font_size
    if args.rotation is not None:
        options["rotation"] = args.rotation

    client = create_client()
    result = await client.watermark_text(args.input, args.text, options or None)
    write_binary_output(result, args.out)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
