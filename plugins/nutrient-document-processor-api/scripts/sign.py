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
from lib.common import (
    create_client,
    write_binary_output,
    assert_local_file,
    read_json_file,
    parse_json_string,
    handle_error,
)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Digitally sign a PDF.",
        epilog="Note: sign() only supports local file inputs for the main PDF.",
    )
    parser.add_argument("--input", required=True, help="Local path to the input PDF.")
    parser.add_argument("--out", required=True, help="Output file path.")
    parser.add_argument(
        "--signature-json-file",
        dest="signature_json_file",
        help="Path to JSON file with signature data.",
    )
    parser.add_argument(
        "--signature-json", dest="signature_json", help="JSON string with signature data."
    )
    parser.add_argument("--image", help="Local path to a signature image.")
    parser.add_argument(
        "--graphic-image", dest="graphic_image", help="Local path to a graphic image."
    )
    args = parser.parse_args()

    input_path = assert_local_file(args.input, "input")

    signature_data = None
    if args.signature_json_file:
        signature_data = read_json_file(args.signature_json_file)
    if args.signature_json:
        signature_data = parse_json_string(args.signature_json)

    options: dict = {}
    if args.image:
        options["image"] = assert_local_file(args.image, "image")
    if args.graphic_image:
        options["graphicImage"] = assert_local_file(args.graphic_image, "graphic-image")

    client = create_client()
    result = await client.sign(input_path, signature_data, options or None)
    write_binary_output(result, args.out)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
