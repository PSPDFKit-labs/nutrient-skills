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
import sys
import tempfile
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
        description="Generate a PDF from Markdown or HTML via Nutrient DWS."
    )
    parser.add_argument("--input", required=True, help="Path to a Markdown or HTML file.")
    parser.add_argument("--out", help="Output PDF path. Defaults to input path with .pdf.")
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
    return parser


async def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    if args.pdfa_level and not args.pdfa:
        parser.error("--pdfa-level requires --pdfa.")
    if args.pdfa and args.pdfa_level is None:
        args.pdfa_level = "pdfa-2b"

    output_path = output_path_for(input_path, args.out)
    html_output_path = html_path_for(output_path)
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
    html_content = compose_input_html(input_path, args)

    if args.html_only or args.output_html:
        html_output_path.parent.mkdir(parents=True, exist_ok=True)
        html_output_path.write_text(html_content, encoding="utf-8")
        if not html_output_path.exists() or html_output_path.stat().st_size == 0:
            raise RuntimeError(f"HTML output was not created or is empty: {html_output_path}")
        # Print immediately so the debug artifact is reported even if the build fails.
        print(html_output_path)

    if args.html_only:
        return

    await build_pdf(html_content, output_path, args)
    print(output_path)


def handle_error(e: Exception) -> NoReturn:
    print(str(e), file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        handle_error(e)
