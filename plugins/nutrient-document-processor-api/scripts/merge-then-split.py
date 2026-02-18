#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["nutrient-dws"]
# ///

"""Merge two PDFs, then split the merged result into two output parts."""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.common import create_client, parse_csv, parse_page_range, write_binary_output, handle_error, fix_negative_args


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge exactly two PDFs, then split into two ranges.",
        epilog=(
            "Example: uv run scripts/merge-then-split.py "
            "--inputs a.pdf,b.pdf --range-a 0:2 --range-b 2: --out-dir out"
        ),
    )
    parser.add_argument(
        "--inputs",
        required=True,
        help="Comma-separated list of exactly 2 local file paths.",
    )
    parser.add_argument("--range-a", dest="range_a", required=True, help="First split range start:end.")
    parser.add_argument("--range-b", dest="range_b", required=True, help="Second split range start:end.")
    parser.add_argument("--out-dir", dest="out_dir", required=True, help="Output directory.")
    args = parser.parse_args(fix_negative_args())

    inputs = parse_csv(args.inputs)
    if len(inputs) != 2:
        parser.error("--inputs must contain exactly 2 local file paths.")

    range_a = parse_page_range(args.range_a)
    range_b = parse_page_range(args.range_b)

    client = create_client()

    # Step 1: merge using client.merge() (two separate API calls as per spec)
    merged = await client.merge(inputs)
    merged_buffer = merged["buffer"]

    # Step 2a: split part-01 — separate workflow call using page range_a
    import asyncio as _asyncio

    async def extract_range(page_range: dict) -> dict:
        result = await (
            client.workflow()
            .add_file_part(merged_buffer, options={"pages": page_range})
            .output_pdf()
            .execute()
        )
        if not result.get("success") or not result.get("output"):
            errors = result.get("errors") or []
            msgs = "; ".join(str(e.get("error", e)) for e in errors)
            raise RuntimeError(f"Split workflow failed: {msgs or 'unknown error'}")
        return result["output"]

    part_a, part_b = await _asyncio.gather(
        extract_range(range_a),
        extract_range(range_b),
    )

    out_dir = Path(args.out_dir)
    write_binary_output(part_a, str(out_dir / "part-01.pdf"))
    write_binary_output(part_b, str(out_dir / "part-02.pdf"))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
