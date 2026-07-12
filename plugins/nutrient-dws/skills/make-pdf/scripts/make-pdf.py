#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["nutrient-dws", "markdown-it-py[linkify,plugins]"]
# ///

import argparse
import asyncio
import html
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NoReturn

from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin


SKILL_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = SKILL_DIR / "assets"
FRONTMATTER_LINE_RE = re.compile(r"^[^:\s][^:]*:\s*.*$")
FRONTMATTER_KEYS = {"title", "subtitle", "author", "date", "template", "theme"}
VALID_TEMPLATES = {"document", "memo"}
VALID_THEMES = {"light", "dark"}
PDFA_LEVELS = [
    "pdfa-1a",
    "pdfa-1b",
    "pdfa-2a",
    "pdfa-2b",
    "pdfa-2u",
    "pdfa-3a",
    "pdfa-3u",
]
INPUT_SUFFIXES = {".md", ".markdown", ".html", ".htm"}
BatchJob = tuple[Path, Path, Path]


@dataclass
class ConversionResult:
    input_path: Path
    created_paths: list[Path] = field(default_factory=list)
    build_error: Exception | None = None
    verification_failed: bool = False
    verified: bool = False


def parse_frontmatter(markdown: str) -> tuple[dict[str, str], str]:
    """Return simple key/value frontmatter and the Markdown body."""
    lines = markdown.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, markdown

    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break

    if end_index is None:
        return {}, markdown

    frontmatter_lines = lines[1:end_index]
    for line in frontmatter_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not FRONTMATTER_LINE_RE.fullmatch(stripped):
            return {}, markdown

    metadata: dict[str, str] = {}
    for line in frontmatter_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, value = stripped.split(":", 1)
        key = key.strip().lower()
        if key not in FRONTMATTER_KEYS:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        metadata[key] = value

    return metadata, "".join(lines[end_index + 1 :])


def markdown_to_html(markdown: str) -> str:
    """Render Markdown with the required GFM-like parser."""
    parser = MarkdownIt("gfm-like").use(tasklists_plugin, enabled=True)
    return parser.render(markdown)


def resolve_metadata(
    frontmatter: dict[str, str],
    overrides: dict[str, str | None] | None = None,
    markdown_body: str = "",
    fallback_title: str = "document",
) -> dict[str, str]:
    """Merge frontmatter and CLI-style overrides, with overrides winning."""
    frontmatter_title = frontmatter.get("title", "")
    override_title = (overrides or {}).get("title")
    metadata = {key: frontmatter.get(key, "") for key in FRONTMATTER_KEYS}
    for key, value in (overrides or {}).items():
        if value is not None:
            metadata[key] = value
    metadata["template"] = metadata.get("template") or "document"
    metadata["theme"] = metadata.get("theme") or "light"
    if metadata["template"] not in VALID_TEMPLATES:
        valid = ", ".join(sorted(VALID_TEMPLATES))
        raise ValueError(f"Invalid template {metadata['template']!r}. Valid values: {valid}.")
    if metadata["theme"] not in VALID_THEMES:
        valid = ", ".join(sorted(VALID_THEMES))
        raise ValueError(f"Invalid theme {metadata['theme']!r}. Valid values: {valid}.")
    title_candidates = (
        override_title,
        frontmatter_title,
        first_atx_h1_text(markdown_body),
        fallback_title,
    )
    metadata["title"] = next(
        (candidate.strip() for candidate in title_candidates if candidate and candidate.strip()),
        "document",
    )
    return metadata


def first_atx_h1_text(markdown: str) -> str:
    """Return the rendered text of the first ATX level-one heading."""
    tokens = MarkdownIt("commonmark").parse(markdown)
    for index, token in enumerate(tokens[:-1]):
        if token.type != "heading_open" or token.tag != "h1" or token.markup != "#":
            continue
        inline = tokens[index + 1]
        return "".join(
            child.content
            for child in (inline.children or [])
            if child.type in {"text", "code_inline", "image"}
        ).strip()
    return ""


def fill_template(
    template_html: str,
    theme_css: str,
    content_html: str,
    metadata: dict[str, str],
) -> str:
    """Replace placeholders in the template without re-scanning inserted values."""
    title = html.escape(metadata.get("title", "").strip() or "document")
    subtitle = html.escape(metadata.get("subtitle", "").strip())
    author = html.escape(metadata.get("author", "").strip())
    date = html.escape(metadata.get("date", "").strip())
    if metadata.get("template") == "memo":
        author_block = f'<p class="memo-author">{author}</p>' if author else ""
        date_block = f'<p class="memo-date">{date}</p>' if date else ""
    else:
        author_block = f'<p class="eyebrow">{author}</p>' if author else ""
        date_block = f'<p class="document-date">{date}</p>' if date else ""
    replacements = {
        "title": title,
        "subtitle_block": f'<p class="subtitle">{subtitle}</p>' if subtitle else "",
        "author_block": author_block,
        "date_block": date_block,
        "content": content_html,
        "styles": theme_css,
    }
    return re.sub(
        r"\{\{\s*(\w+)\s*\}\}",
        lambda match: replacements.get(match.group(1), ""),
        template_html,
    )


def compose_markdown_html(
    markdown: str,
    template_html: str,
    theme_css: str,
    overrides: dict[str, str | None] | None = None,
    fallback_title: str = "document",
) -> tuple[str, dict[str, str]]:
    """Convert Markdown with frontmatter into final HTML."""
    frontmatter, body = parse_frontmatter(markdown)
    metadata = resolve_metadata(frontmatter, overrides, body, fallback_title)
    content_html = markdown_to_html(body)
    return fill_template(template_html, theme_css, content_html, metadata), metadata


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def output_path_for(input_path: Path, out: str | None) -> Path:
    if out:
        return Path(out)
    return input_path.with_suffix(".pdf")


def html_path_for(output_path: Path) -> Path:
    return output_path.with_suffix(".html")


def plan_batch(input_dir: Path, out_dir: Path) -> list[BatchJob]:
    """Return deterministic, non-recursive conversion jobs without writing files."""
    input_paths = sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in INPUT_SUFFIXES
    )
    jobs = [
        (input_path, out_dir / f"{input_path.stem}.pdf", out_dir / f"{input_path.stem}.html")
        for input_path in input_paths
    ]
    # Keyed casefolded so Report.md and report.html collide here rather than
    # silently overwriting each other on case-insensitive filesystems (APFS, NTFS).
    output_owners: dict[str, Path] = {}
    for input_path, pdf_path, html_path in jobs:
        for output_path in (pdf_path, html_path):
            key = str(output_path).casefold()
            owner = output_owners.get(key)
            if owner is not None:
                raise ValueError(
                    "Batch inputs would overwrite the same output "
                    f"{output_path}: {owner.name}, {input_path.name}"
                )
            output_owners[key] = input_path
    return jobs


def load_template(name: str) -> str:
    return read_text(ASSETS_DIR / "templates" / f"{name}.html")


def load_theme(name: str) -> str:
    return read_text(ASSETS_DIR / "themes" / f"{name}.css")


def compose_input_html(input_path: Path, args: argparse.Namespace) -> str:
    suffix = input_path.suffix.lower()
    if suffix in {".html", ".htm"}:
        return read_text(input_path)
    if suffix not in {".md", ".markdown"}:
        raise ValueError("--input must point to a .md, .markdown, .html, or .htm file.")

    markdown = read_text(input_path)
    frontmatter, body = parse_frontmatter(markdown)
    resolved = resolve_metadata(
        frontmatter,
        {
            "title": args.title,
            "subtitle": args.subtitle,
            "author": args.author,
            "date": args.date,
            "template": args.template,
            "theme": args.theme,
        },
        body,
        input_path.stem,
    )
    template_html = load_template(resolved["template"])
    theme_css = load_theme(resolved["theme"])
    return fill_template(template_html, theme_css, markdown_to_html(body), resolved)


def create_client():
    api_key = os.environ.get("NUTRIENT_API_KEY") or os.environ.get("NUTRIENT_DWS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "NUTRIENT_API_KEY is not set. Export it before generating PDFs, "
            "or use --html-only to render HTML offline."
        )
    try:
        from nutrient_dws import NutrientClient
    except ImportError as e:
        raise RuntimeError(
            "Unable to import nutrient_dws. Re-run with uv so script dependencies install.\n"
            f"Original error: {e}"
        ) from e
    return NutrientClient(api_key=api_key)


def workflow_error_message(result: dict[str, Any]) -> str:
    errors = result.get("errors") or []
    messages = []
    for error in errors:
        value = error.get("error", error) if isinstance(error, dict) else error
        messages.append(str(value))
    return "; ".join(messages) or "unknown error"


def write_workflow_output(result: dict[str, Any], output_path: Path) -> None:
    if not result.get("success") or not result.get("output"):
        raise RuntimeError(f"Workflow failed: {workflow_error_message(result)}")

    buffer = result["output"].get("buffer")
    if not buffer:
        raise RuntimeError("Workflow succeeded but returned an empty output buffer.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(buffer)
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"Output was not created or is empty: {output_path}")


async def build_pdf(html_content: str, output_path: Path, args: argparse.Namespace) -> None:
    try:
        from nutrient_dws.builder.constant import BuildActions
    except ImportError as e:
        raise RuntimeError(
            "Unable to import nutrient_dws builder helpers. Re-run with uv so script dependencies install.\n"
            f"Original error: {e}"
        ) from e

    print("Preparing HTML for Nutrient DWS Build API.", file=sys.stderr)
    client = create_client()
    with tempfile.TemporaryDirectory() as tmpdir:
        html_input = Path(tmpdir) / "input.html"
        html_input.write_text(html_content, encoding="utf-8")

        workflow = client.workflow().add_html_part(str(html_input))
        if args.watermark:
            workflow = workflow.apply_action(
                BuildActions.watermark_text(
                    args.watermark,
                    {
                        "opacity": 0.1,
                        "fontSize": 72,
                        "rotation": 45,
                        "fontFamily": "Helvetica",
                    },
                )
            )

        if args.accessible:
            workflow = workflow.output_pdfua()
        elif args.pdfa:
            workflow = workflow.output_pdfa({"conformance": args.pdfa_level})
        else:
            workflow = workflow.output_pdf()

        print("Calling Nutrient DWS Build API.", file=sys.stderr)
        result = await workflow.execute(
            on_progress=lambda step, total: print(
                f"Build progress: {step}/{total}", file=sys.stderr
            )
        )

    write_workflow_output(result, output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate PDFs from Markdown or HTML via Nutrient DWS.",
        epilog="Exit codes: 0 = success; 1 = build/compose failure; "
        "3 = generated but failed verification.",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to a Markdown/HTML file or a directory of input files (non-recursive).",
    )
    parser.add_argument(
        "--out",
        help="Output PDF path, or required output directory for directory input.",
    )
    parser.add_argument(
        "--template",
        choices=["document", "memo"],
        help="Template for Markdown input. Default: document.",
    )
    parser.add_argument(
        "--theme",
        choices=["light", "dark"],
        help="Theme for Markdown input. Default: light.",
    )
    parser.add_argument("--title", help="Document title.")
    parser.add_argument("--subtitle", help="Document subtitle.")
    parser.add_argument("--author", help="Document author.")
    parser.add_argument("--date", help="Document date.")
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--accessible",
        action="store_true",
        help="Generate accessible PDF/UA output.",
    )
    output_group.add_argument(
        "--pdfa",
        action="store_true",
        help="Generate archival PDF/A output.",
    )
    parser.add_argument(
        "--pdfa-level",
        choices=PDFA_LEVELS,
        default=None,
        help="PDF/A conformance level. Requires --pdfa; default with --pdfa: pdfa-2b.",
    )
    parser.add_argument("--watermark", metavar="TEXT", help="Apply a diagonal text watermark.")
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="Write the composed HTML next to the output path and skip the API call.",
    )
    parser.add_argument(
        "--output-html",
        action="store_true",
        help="Write the composed HTML next to the PDF output path.",
    )
    parser.add_argument(
        "--verify",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Verify PDF structure (default: on for --accessible/--pdfa, off otherwise).",
    )
    return parser


def validate_file_job(
    input_path: Path,
    html_output_path: Path,
    args: argparse.Namespace,
) -> None:
    is_html_input = input_path.suffix.lower() in {".html", ".htm"}
    if args.html_only and is_html_input:
        raise ValueError("--html-only cannot be used with HTML input; the input already is HTML.")
    if (
        (args.html_only or args.output_html)
        and html_output_path.resolve() == input_path.resolve()
    ):
        raise ValueError(
            f"HTML output path resolves to the input file: {input_path}. "
            "Use --out to choose a different output base."
        )
    if is_html_input:
        ignored_flags = [
            flag
            for flag, value in (
                ("--template", args.template),
                ("--theme", args.theme),
                ("--title", args.title),
                ("--subtitle", args.subtitle),
                ("--author", args.author),
                ("--date", args.date),
            )
            if value is not None
        ]
        if ignored_flags:
            print(
                f"Warning: HTML input ignores these flags: {', '.join(ignored_flags)}.",
                file=sys.stderr,
            )


async def verify_output(output_path: Path, args: argparse.Namespace) -> tuple[bool, bool]:
    """Return whether verification passed and whether the verifier ran.

    Verification was explicitly requested for a compliance build, so an
    inability to verify is reported as a failure (exit 3), never as success —
    pass --no-verify to accept unverified output.
    """
    uv = shutil.which("uv")
    if uv is None:
        print(
            f"Verification required but uv is not on PATH for {output_path}; "
            "treating as unverified (use --no-verify to accept unverified output).",
            file=sys.stderr,
        )
        return False, False

    if args.accessible:
        profile = "pdfua"
    elif args.pdfa:
        profile = "pdfa"
    else:
        profile = "auto"
    command = [
        uv,
        "run",
        str(SKILL_DIR / "scripts" / "verify-pdf.py"),
        "--input",
        str(output_path),
        "--profile",
        profile,
    ]
    if args.pdfa:
        command.extend(["--pdfa-level", args.pdfa_level])

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
    )
    await process.communicate()
    if process.returncode == 0:
        return True, True
    if process.returncode == 1:
        print(
            f"Verification failed conformance checks for {output_path}; "
            "keeping the generated PDF.",
            file=sys.stderr,
        )
    else:
        print(
            f"Verifier could not run for {output_path} "
            f"(exit {process.returncode}); treating as unverified and "
            "keeping the generated PDF.",
            file=sys.stderr,
        )
    return False, True


async def convert_one(
    input_path: Path,
    output_path: Path,
    html_output_path: Path,
    args: argparse.Namespace,
    *,
    emit_paths: bool = False,
    refuse_overwrite: bool = False,
) -> ConversionResult:
    result = ConversionResult(input_path=input_path)
    try:
        validate_file_job(input_path, html_output_path, args)
        if refuse_overwrite:
            guarded_outputs = []
            if args.html_only or args.output_html:
                guarded_outputs.append(html_output_path)
            if not args.html_only:
                guarded_outputs.append(output_path)
            for guarded_output in guarded_outputs:
                if guarded_output.exists():
                    raise FileExistsError(
                        f"Refusing to overwrite existing output: {guarded_output}"
                    )
        html_content = compose_input_html(input_path, args)

        if args.html_only or args.output_html:
            html_output_path.parent.mkdir(parents=True, exist_ok=True)
            html_output_path.write_text(html_content, encoding="utf-8")
            if not html_output_path.exists() or html_output_path.stat().st_size == 0:
                raise RuntimeError(
                    f"HTML output was not created or is empty: {html_output_path}"
                )
            result.created_paths.append(html_output_path)
            if emit_paths:
                print(html_output_path)

        if args.html_only:
            return result

        await build_pdf(html_content, output_path, args)
        result.created_paths.append(output_path)
        if args.verify:
            try:
                passed, ran = await verify_output(output_path, args)
                result.verified = ran and passed
                result.verification_failed = not passed
            except Exception as error:
                print(
                    f"Verification failed for {output_path}: {error}; "
                    "keeping the generated PDF.",
                    file=sys.stderr,
                )
                result.verification_failed = True
        if emit_paths:
            print(output_path)
    except Exception as error:
        result.build_error = error
    return result


async def run_single(input_path: Path, args: argparse.Namespace) -> int:
    output_path = output_path_for(input_path, args.out)
    result = await convert_one(
        input_path,
        output_path,
        html_path_for(output_path),
        args,
        emit_paths=True,
    )
    if result.build_error:
        raise result.build_error
    return 3 if result.verification_failed else 0


async def run_batch(input_dir: Path, out_dir: Path, args: argparse.Namespace) -> int:
    jobs = plan_batch(input_dir, out_dir)
    if not jobs:
        raise ValueError(
            f"No .md, .markdown, .html, or .htm files found in directory: {input_dir}"
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(4)

    async def run_job(job: BatchJob) -> ConversionResult:
        async with semaphore:
            return await convert_one(*job, args, refuse_overwrite=True)

    results = await asyncio.gather(*(run_job(job) for job in jobs))
    for result in results:
        for created_path in result.created_paths:
            print(created_path)

    converted = sum(result.build_error is None for result in results)
    summary = f"converted {converted}/{len(results)}"
    if args.verify and not args.html_only:
        verified = sum(result.verified for result in results)
        summary += f"; verified {verified}/{converted}"
    failures = [
        result.input_path.name
        for result in results
        if result.build_error or result.verification_failed
    ]
    if failures:
        summary += f"; failures: {', '.join(failures)}"
    for result in results:
        if result.build_error:
            print(f"{result.input_path.name}: {result.build_error}", file=sys.stderr)
    print(summary, file=sys.stderr)

    if any(result.build_error for result in results):
        return 1
    if any(result.verification_failed for result in results):
        return 3
    return 0


async def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    if args.pdfa_level and not args.pdfa:
        parser.error("--pdfa-level requires --pdfa.")
    if args.pdfa and args.pdfa_level is None:
        args.pdfa_level = "pdfa-2b"
    if args.verify is True and not (args.accessible or args.pdfa):
        parser.error(
            "--verify requires --accessible or --pdfa; a standard PDF carries "
            "no conformance claim to check."
        )
    if args.verify is None:
        args.verify = args.accessible or args.pdfa

    if input_path.is_dir():
        if not args.out:
            parser.error("--out is required when --input is a directory.")
        if args.title is not None or args.subtitle is not None:
            parser.error("--title and --subtitle cannot be used with directory input.")
        out_dir = Path(args.out)
        if out_dir.exists() and not out_dir.is_dir():
            raise ValueError(f"Batch output path is not a directory: {out_dir}")
        return await run_batch(input_path, out_dir, args)

    if not input_path.is_file():
        raise ValueError(f"Input path is not a file or directory: {input_path}")
    return await run_single(input_path, args)


def handle_error(e: Exception) -> NoReturn:
    print(str(e), file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception as e:
        handle_error(e)
