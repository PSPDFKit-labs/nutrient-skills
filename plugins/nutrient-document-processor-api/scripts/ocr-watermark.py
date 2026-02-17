#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["nutrient-dws"]
# ///

"""OCR a document and stamp it with a text watermark in one pipeline."""

import argparse
import asyncio
import sys
from pathlib import Path

from nutrient_dws.builder.constant import BuildActions

sys.path.insert(0, str(Path(__file__).parent))
from lib.common import create_client, write_workflow_output, handle_error


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="OCR a document then stamp it with a text watermark.",
        epilog=(
            "Example: uv run scripts/ocr-watermark.py "
            "--input scan.pdf --text CONFIDENTIAL --out scan-ocr-watermarked.pdf"
        ),
    )
    parser.add_argument("--input", required=True, help="Path or URL to the input document.")
    parser.add_argument("--out", required=True, help="Output file path.")
    parser.add_argument(
        "--languages",
        default="english",
        help="Comma-separated OCR language(s) (default: english).",
    )
    parser.add_argument(
        "--text",
        default="CONFIDENTIAL",
        help="Watermark text (default: CONFIDENTIAL).",
    )
    parser.add_argument(
        "--opacity",
        type=float,
        default=0.3,
        help="Watermark opacity 0.0-1.0 (default: 0.3).",
    )
    parser.add_argument(
        "--rotation",
        type=int,
        default=45,
        help="Watermark rotation in degrees (default: 45).",
    )
    parser.add_argument(
        "--font-size",
        dest="font_size",
        type=int,
        default=72,
        help="Watermark font size in points (default: 72).",
    )
    args = parser.parse_args()

    # Build the language argument — single string or list for multiple.
    raw_languages = [lang.strip() for lang in args.languages.split(",") if lang.strip()]
    language_arg = raw_languages[0] if len(raw_languages) == 1 else raw_languages

    watermark_options = {
        "opacity": args.opacity,
        "rotation": args.rotation,
        "fontSize": args.font_size,
    }

    client = create_client()

    actions = [
        BuildActions.ocr(language_arg),
        BuildActions.watermark_text(args.text, watermark_options),
    ]

    result = await (
        client.workflow()
        .add_file_part(args.input, actions=actions)
        .output_pdf()
        .execute()
    )
    write_workflow_output(result, args.out)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
