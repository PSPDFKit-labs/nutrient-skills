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
    parser = argparse.ArgumentParser(
        description="Extract text from a document as JSON, with optional plain-text export."
    )
    parser.add_argument("--input", required=True, help="Path or URL to the input document.")
    parser.add_argument("--out", required=True, help="Output JSON file path.")
    parser.add_argument("--pages", help="Page range in start:end format.")
    parser.add_argument("--plain-out", dest="plain_out", help="Optional plain-text output file.")
    args = parser.parse_args(fix_negative_args())

    pages = parse_page_range(args.pages) if args.pages else None

    client = create_client()
    result = await client.extract_text(args.input, pages)
    write_json_output(result, args.out)

    if args.plain_out:
        text = "\n\n".join(
            page.get("plainText", "")
            for page in result["data"].get("pages", [])
            if page.get("plainText")
        )
        plain_path = Path(args.plain_out)
        plain_path.parent.mkdir(parents=True, exist_ok=True)
        plain_path.write_text(text, encoding="utf-8")
        print(f"Wrote {args.plain_out}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
