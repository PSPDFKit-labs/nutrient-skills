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
    parser = argparse.ArgumentParser(description="Protect a PDF with user/owner passwords.")
    parser.add_argument("--input", required=True, help="Path or URL to the input PDF.")
    parser.add_argument(
        "--user-password", dest="user_password", required=True, help="User password."
    )
    parser.add_argument(
        "--owner-password", dest="owner_password", required=True, help="Owner password."
    )
    parser.add_argument("--out", required=True, help="Output file path.")
    parser.add_argument("--permissions", help="Comma-separated list of permissions.")
    args = parser.parse_args()

    permissions = parse_csv(args.permissions) if args.permissions else None

    client = create_client()
    result = await client.password_protect(
        args.input, args.user_password, args.owner_password, permissions
    )
    write_binary_output(result, args.out)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
