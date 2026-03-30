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
from lib.common import create_client, write_binary_output, parse_csv, handle_error


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run OCR on a document.",
        epilog="Example: uv run scripts/ocr.py --input scan.pdf --languages english --out scan-ocr.pdf",
    )
    parser.add_argument("--input", required=True, help="Path or URL to the input document.")
    parser.add_argument(
        "--languages", required=True, help="Comma-separated language(s) for OCR (e.g. english,german)."
    )
    parser.add_argument("--out", required=True, help="Output file path.")
    args = parser.parse_args()

    languages = parse_csv(args.languages)
    language_arg = languages[0] if len(languages) == 1 else languages

    client = create_client()
    result = await client.ocr(args.input, language_arg)
    write_binary_output(result, args.out)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
