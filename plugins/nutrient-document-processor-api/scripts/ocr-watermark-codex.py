#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["nutrient-dws"]
# ///

import argparse
import asyncio
import sys
from pathlib import Path

from nutrient_dws.builder.constant import BuildActions

sys.path.insert(0, str(Path(__file__).parent))
from lib.common import create_client, write_workflow_output, handle_error


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="OCR a PDF and stamp it with a DRAFT watermark.",
        epilog="Example: uv run scripts/ocr-watermark-codex.py --input scan.pdf --out result.pdf",
    )
    parser.add_argument("--input", required=True, help="Path or URL to the input document.")
    parser.add_argument("--out", required=True, help="Output file path.")
    parser.add_argument(
        "--language",
        default="english",
        help="OCR language (default: english).",
    )
    parser.add_argument(
        "--watermark-text",
        dest="watermark_text",
        default="DRAFT",
        help="Watermark text to stamp on every page (default: DRAFT).",
    )
    parser.add_argument(
        "--opacity",
        type=float,
        default=0.25,
        help="Watermark opacity 0.0-1.0 (default: 0.25).",
    )
    parser.add_argument(
        "--rotation",
        type=int,
        default=45,
        help="Watermark rotation in degrees as an integer (default: 45).",
    )
    args = parser.parse_args()

    client = create_client()

    actions = [
        BuildActions.ocr(args.language),
        BuildActions.watermark_text(
            args.watermark_text,
            {"opacity": args.opacity, "rotation": args.rotation},
        ),
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
