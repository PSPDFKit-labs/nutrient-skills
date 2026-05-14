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
from lib.common import create_client, write_binary_output, parse_page_range, handle_error, fix_negative_args


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create AI redactions and optionally apply them.",
        epilog='Example: uv run scripts/redact-ai.py --input policy.pdf --criteria "Remove all emails" --mode apply --out redacted.pdf',
    )
    parser.add_argument("--input", required=True, help="Path or URL to the input document.")
    parser.add_argument("--criteria", required=True, help="Natural-language redaction criteria.")
    parser.add_argument("--out", required=True, help="Output file path.")
    parser.add_argument(
        "--mode",
        default="stage",
        choices=["stage", "apply"],
        help="Redaction mode: stage (default) or apply.",
    )
    parser.add_argument("--pages", help="Page range in start:end format.")
    args = parser.parse_args(fix_negative_args())

    pages = parse_page_range(args.pages) if args.pages else None

    client = create_client()
    result = await client.create_redactions_ai(args.input, args.criteria, args.mode, pages)
    write_binary_output(result, args.out)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
