#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pikepdf"]
# ///

"""Check structural PDF/UA and PDF/A conformance signals."""

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar

import pikepdf


PDFA_LEVELS = (
    "pdfa-1a",
    "pdfa-1b",
    "pdfa-2a",
    "pdfa-2b",
    "pdfa-2u",
    "pdfa-3a",
    "pdfa-3u",
)
PdfSource = pikepdf.Pdf | str | Path
T = TypeVar("T")


@dataclass(frozen=True)
class CheckResult:
    """One side-effect-free structural check result."""

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class FileResult:
    """The complete verification result for one PDF."""

    path: str
    profiles: tuple[str, ...]
    passed: bool
    checks: tuple[CheckResult, ...]
    verapdf: CheckResult | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["profiles"] = list(self.profiles)
        value["checks"] = [asdict(check) for check in self.checks]
        value["verapdf"] = asdict(self.verapdf) if self.verapdf else None
        return value


def _with_pdf(source: PdfSource, operation: Callable[[pikepdf.Pdf], T]) -> T:
    """Run a pure inspection against an open PDF or a path."""
    if isinstance(source, pikepdf.Pdf):
        return operation(source)
    with pikepdf.open(Path(source)) as pdf:
        return operation(pdf)


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, dict):
        return any(_nonempty(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_nonempty(item) for item in value)
    return bool(str(value).strip())


def _metadata_value(metadata: Any, key: str) -> str:
    value = metadata.get(key)
    if value is None:
        return ""
    if isinstance(value, dict):
        for preferred in ("x-default", "en-US", "en"):
            if _nonempty(value.get(preferred)):
                return str(value[preferred]).strip()
        return next((str(item).strip() for item in value.values() if _nonempty(item)), "")
    if isinstance(value, (list, tuple)):
        return next((str(item).strip() for item in value if _nonempty(item)), "")
    return str(value).strip()


def read_xmp_claims(source: PdfSource) -> dict[str, str]:
    """Return the PDF/UA and PDF/A identification values carried in XMP."""

    def inspect(pdf: pikepdf.Pdf) -> dict[str, str]:
        with pdf.open_metadata(set_pikepdf_as_editor=False) as metadata:
            return {
                "pdfuaid:part": _metadata_value(metadata, "pdfuaid:part"),
                "pdfaid:part": _metadata_value(metadata, "pdfaid:part"),
                "pdfaid:conformance": _metadata_value(metadata, "pdfaid:conformance"),
            }

    return _with_pdf(source, inspect)


def check_common(source: PdfSource) -> list[CheckResult]:
    """Check signals required of every input PDF."""

    def inspect(pdf: pikepdf.Pdf) -> list[CheckResult]:
        page_count = len(pdf.pages)
        return [
            CheckResult("file opens", True, "opened successfully"),
            CheckResult(
                "page count",
                page_count >= 1,
                f"{page_count} page{'s' if page_count != 1 else ''}",
            ),
        ]

    return _with_pdf(source, inspect)


def check_pdfua(source: PdfSource) -> list[CheckResult]:
    """Check the requested PDF/UA-1 structural signals."""

    def inspect(pdf: pikepdf.Pdf) -> list[CheckResult]:
        root = pdf.Root
        mark_info = root.get("/MarkInfo")
        marked = (
            mark_info.get("/Marked")
            if isinstance(mark_info, pikepdf.Dictionary)
            else None
        )
        struct_tree = root.get("/StructTreeRoot")
        lang = root.get("/Lang")
        viewer_preferences = root.get("/ViewerPreferences")
        display_doc_title = (
            viewer_preferences.get("/DisplayDocTitle")
            if isinstance(viewer_preferences, pikepdf.Dictionary)
            else None
        )
        info_title = pdf.docinfo.get("/Title")
        with pdf.open_metadata(set_pikepdf_as_editor=False) as metadata:
            ua_part = _metadata_value(metadata, "pdfuaid:part")
            xmp_title = _metadata_value(metadata, "dc:title")

        return [
            CheckResult(
                "pdfuaid:part",
                ua_part == "1",
                f"expected 1, found {ua_part or 'missing'}",
            ),
            CheckResult(
                "MarkInfo/Marked",
                marked is True,
                "true" if marked is True else "missing, false, or not a boolean",
            ),
            CheckResult(
                "StructTreeRoot",
                struct_tree is not None,
                "present" if struct_tree is not None else "missing",
            ),
            CheckResult(
                "Lang",
                _nonempty(lang),
                str(lang).strip() if _nonempty(lang) else "missing or empty",
            ),
            CheckResult(
                "ViewerPreferences/DisplayDocTitle",
                display_doc_title is True,
                "true"
                if display_doc_title is True
                else "missing, false, or not a boolean",
            ),
            CheckResult(
                "document title",
                _nonempty(xmp_title) or _nonempty(info_title),
                "present in XMP dc:title"
                if _nonempty(xmp_title)
                else "present in DocInfo /Title"
                if _nonempty(info_title)
                else "missing or empty",
            ),
        ]

    return _with_pdf(source, inspect)


def check_pdfa(source: PdfSource, pdfa_level: str | None = None) -> list[CheckResult]:
    """Check PDF/A identification, optionally against a requested level."""
    if pdfa_level is not None and pdfa_level not in PDFA_LEVELS:
        raise ValueError(f"Unsupported PDF/A level: {pdfa_level}")

    def inspect(pdf: pikepdf.Pdf) -> list[CheckResult]:
        claims = read_xmp_claims(pdf)
        part = claims["pdfaid:part"]
        conformance = claims["pdfaid:conformance"]
        checks = [
            CheckResult(
                "pdfaid:part",
                _nonempty(part),
                part if part else "missing",
            ),
            CheckResult(
                "pdfaid:conformance",
                _nonempty(conformance),
                conformance if conformance else "missing",
            ),
        ]
        if pdfa_level:
            level = pdfa_level.removeprefix("pdfa-")
            expected_part = level[:-1]
            expected_conformance = level[-1].upper()
            checks.extend(
                [
                    CheckResult(
                        "requested PDF/A part",
                        part == expected_part,
                        f"expected {expected_part}, found {part or 'missing'}",
                    ),
                    CheckResult(
                        "requested PDF/A conformance",
                        conformance.upper() == expected_conformance,
                        f"expected {expected_conformance}, found {conformance or 'missing'}",
                    ),
                ]
            )
        return checks

    return _with_pdf(source, inspect)


def _profiles_for(pdf: pikepdf.Pdf, requested: str) -> tuple[str, ...]:
    if requested != "auto":
        return (requested,)
    claims = read_xmp_claims(pdf)
    profiles = []
    if claims["pdfuaid:part"]:
        profiles.append("pdfua")
    if claims["pdfaid:part"] or claims["pdfaid:conformance"]:
        profiles.append("pdfa")
    return tuple(profiles)


def _verapdf_flavour(
    profile: str, pdfa_level: str | None, claims: dict[str, str]
) -> str | None:
    if profile == "pdfua":
        return "ua1"
    if pdfa_level:
        return pdfa_level.removeprefix("pdfa-")
    part = claims["pdfaid:part"]
    conformance = claims["pdfaid:conformance"].lower()
    return f"{part}{conformance}" if part and conformance else None


def _verdict_line(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in reversed(lines):
        lowered = line.lower()
        if "compliant" in lowered or "validation result" in lowered:
            return line
    return lines[-1] if lines else "veraPDF exited without a verdict line"


def run_verapdf(path: Path, flavour: str, executable: str) -> CheckResult:
    """Run veraPDF and return its process verdict without printing."""
    try:
        process = subprocess.run(
            [executable, "--flavour", flavour, str(path)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CheckResult("veraPDF", False, "timed out after 120 seconds")
    except OSError as error:
        return CheckResult("veraPDF", False, f"could not run: {error}")
    combined = "\n".join(value for value in (process.stdout, process.stderr) if value)
    return CheckResult(
        "veraPDF",
        process.returncode == 0,
        f"{_verdict_line(combined)} (exit {process.returncode}, flavour {flavour})",
    )


def verify_file(
    path: Path,
    profile: str = "auto",
    pdfa_level: str | None = None,
    verapdf_executable: str | None = None,
) -> FileResult:
    """Verify one file without producing output."""
    try:
        with pikepdf.open(path) as pdf:
            checks = check_common(pdf)
            profiles = _profiles_for(pdf, profile)
            if pdfa_level and "pdfa" not in profiles:
                profiles = (*profiles, "pdfa")
            if not profiles:
                checks.append(
                    CheckResult(
                        "XMP conformance claim",
                        False,
                        "auto profile found neither a PDF/UA nor PDF/A claim",
                    )
                )
            for selected in profiles:
                checks.extend(
                    check_pdfua(pdf)
                    if selected == "pdfua"
                    else check_pdfa(pdf, pdfa_level)
                )
            claims = read_xmp_claims(pdf)
    except pikepdf.PdfError as error:
        checks = [CheckResult("file opens", False, str(error))]
        profiles = (profile,) if profile != "auto" else ()
        claims = {"pdfuaid:part": "", "pdfaid:part": "", "pdfaid:conformance": ""}

    verapdf_result = None
    if verapdf_executable and profiles:
        vera_results = []
        for selected in profiles:
            flavour = _verapdf_flavour(selected, pdfa_level, claims)
            if flavour:
                vera_results.append(run_verapdf(path, flavour, verapdf_executable))
            else:
                vera_results.append(
                    CheckResult("veraPDF", False, "unable to determine PDF/A flavour")
                )
        verapdf_result = CheckResult(
            "veraPDF",
            all(result.passed for result in vera_results),
            "; ".join(result.detail for result in vera_results),
        )

    passed = all(check.passed for check in checks) and (
        verapdf_result is None or verapdf_result.passed
    )
    return FileResult(
        str(path), profiles, passed, tuple(checks), verapdf_result
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check PDF/UA and PDF/A structural conformance signals — not a full "
            "conformance audit. When installed, veraPDF is also run for a full audit."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="A .pdf file or a directory of .pdf files (non-recursive).",
    )
    parser.add_argument(
        "--profile",
        choices=("pdfua", "pdfa", "auto"),
        default="auto",
        help="Profile to check; auto checks the conformance claims found in XMP.",
    )
    parser.add_argument(
        "--pdfa-level",
        choices=PDFA_LEVELS,
        help="Assert that XMP identifies this exact PDF/A part and conformance level.",
    )
    parser.add_argument(
        "--json", action="store_true", help="Write a machine-readable JSON array to stdout."
    )
    return parser


def _input_files(input_path: Path) -> list[Path]:
    if not input_path.exists():
        raise OSError(f"Input does not exist: {input_path}")
    if input_path.is_dir():
        files = sorted(
            path
            for path in input_path.iterdir()
            if path.is_file() and path.suffix.lower() == ".pdf"
        )
        if not files:
            raise OSError(f"No .pdf files found in directory: {input_path}")
        return files
    if not input_path.is_file() or input_path.suffix.lower() != ".pdf":
        raise OSError(f"--input must be a .pdf file or a directory: {input_path}")
    return [input_path]


def _print_result(result: FileResult) -> None:
    for check in result.checks:
        mark = "✓" if check.passed else "✗"
        print(f"{mark} {result.path}: {check.name} — {check.detail}", file=sys.stderr)
    if result.verapdf:
        mark = "✓" if result.verapdf.passed else "✗"
        print(
            f"{mark} {result.path}: {result.verapdf.name} — {result.verapdf.detail}",
            file=sys.stderr,
        )
    verdict = "PASS" if result.passed else "FAIL"
    print(f"VERDICT {verdict} {result.path}", file=sys.stderr)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.pdfa_level and args.profile == "pdfua":
        parser.error("--pdfa-level cannot be used with --profile pdfua.")

    try:
        paths = _input_files(Path(args.input))
    except OSError as error:
        print(str(error), file=sys.stderr)
        return 2

    verapdf_executable = shutil.which("verapdf")
    if verapdf_executable is None:
        print(
            "Hint: structural checks only; install veraPDF for a full conformance audit.",
            file=sys.stderr,
        )

    try:
        results = [
            verify_file(path, args.profile, args.pdfa_level, verapdf_executable)
            for path in paths
        ]
    except OSError as error:
        print(str(error), file=sys.stderr)
        return 2
    for result in results:
        _print_result(result)

    if args.json:
        print(json.dumps([result.to_dict() for result in results], ensure_ascii=False))
    else:
        for result in results:
            print(f"{'PASS' if result.passed else 'FAIL'} {result.path}")
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
