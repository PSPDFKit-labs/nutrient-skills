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

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from lib.common import create_client, write_workflow_output, handle_error


async def main() -> None:
    parser = argparse.ArgumentParser(description="Template for multi-step custom workflows.")
    parser.add_argument("--input", required=True, help="Path or URL to the input document.")
    parser.add_argument("--out", required=True, help="Output file path.")
    args = parser.parse_args()

    client = create_client()

    # Customize this action list for the requested pipeline.
    actions = [
        BuildActions.ocr("english"),
        BuildActions.watermark_text("DRAFT", {"opacity": 0.25, "rotation": 45}),
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
