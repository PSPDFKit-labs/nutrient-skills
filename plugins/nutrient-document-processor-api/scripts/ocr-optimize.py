#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["nutrient-dws"]
# ///

"""OCR a document and optimize the resulting PDF in one workflow."""

import argparse
import asyncio
import sys
from pathlib import Path

from nutrient_dws.builder.constant import BuildActions

sys.path.insert(0, str(Path(__file__).parent))
from lib.common import create_client, write_workflow_output, handle_error


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run OCR then optimize the output PDF.",
        epilog=(
            "Example: uv run scripts/ocr-optimize.py "
            "--input scan.pdf --language english --out out.pdf"
        ),
    )
    parser.add_argument("--input", required=True, help="Path or URL to the input document.")
    parser.add_argument("--out", required=True, help="Output file path.")
    parser.add_argument(
        "--language",
        default="english",
        help="OCR language (default: english).",
    )
    args = parser.parse_args()

    actions = [
        BuildActions.ocr(args.language),
    ]

    client = create_client()
    result = await (
        client.workflow()
        .add_file_part(args.input, actions=actions)
        .output_pdf({"optimize": {"imageOptimizationQuality": 2}})
        .execute()
    )
    write_workflow_output(result, args.out)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
