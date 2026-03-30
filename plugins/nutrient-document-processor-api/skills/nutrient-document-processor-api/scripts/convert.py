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
    parser = argparse.ArgumentParser(description="Convert a document to another format.")
    parser.add_argument("--input", required=True, help="Path or URL to the input document.")
    parser.add_argument(
        "--format",
        required=True,
        help="Target format: pdf, pdfa, pdfua, docx, xlsx, pptx, png, jpeg, jpg, webp, html, markdown",
    )
    parser.add_argument("--out", required=True, help="Output file path.")
    args = parser.parse_args()

    client = create_client()
    result = await client.convert(args.input, args.format)
    write_binary_output(result, args.out)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
