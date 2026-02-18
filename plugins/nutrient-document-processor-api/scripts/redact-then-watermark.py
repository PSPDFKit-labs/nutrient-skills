#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["nutrient-dws"]
# ///

"""AI-redact content (apply mode) then stamp a REDACTED watermark on every page.

Two-step pipeline using public SDK calls:
  1. client.create_redactions_ai() — redacts content matching the criteria
  2. client.workflow() with BuildActions.watermark_text() — stamps the watermark
"""

import argparse
import asyncio
import sys
from pathlib import Path

from nutrient_dws.builder.constant import BuildActions

sys.path.insert(0, str(Path(__file__).parent))
from lib.common import create_client, write_workflow_output, handle_error


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI-redact content then stamp a REDACTED watermark on every page.",
        epilog=(
            "Example: uv run scripts/redact-then-watermark.py "
            "--input doc.pdf --criteria 'Remove all email addresses' --out out.pdf"
        ),
    )
    parser.add_argument("--input", required=True, help="Path or URL to the input PDF.")
    parser.add_argument("--criteria", required=True, help="Natural-language redaction criteria.")
    parser.add_argument("--out", required=True, help="Output file path.")
    args = parser.parse_args()

    client = create_client()

    # Step 1: AI-redact in apply mode using the public SDK method.
    redact_result = await client.create_redactions_ai(args.input, args.criteria, "apply")
    redacted_bytes: bytes = redact_result["buffer"]

    # Step 2: Stamp a watermark on the redacted PDF via a workflow call.
    actions = [
        BuildActions.watermark_text("REDACTED", {"opacity": 0.3, "rotation": 45, "fontSize": 72}),
    ]

    result = await (
        client.workflow()
        .add_file_part(redacted_bytes, actions=actions)
        .output_pdf()
        .execute()
    )
    write_workflow_output(result, args.out)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
