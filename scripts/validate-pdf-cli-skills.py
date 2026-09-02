#!/usr/bin/env python3

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SHELL_FILES = [
    ROOT / "plugins/pdf-to-markdown/skills/pdf-to-markdown/bin/pdf-to-markdown",
    ROOT / "plugins/pdf-to-markdown/skills/pdf-to-markdown/bin/nutrient",
    ROOT / "plugins/pdf-to-text/skills/pdf-to-text/bin/pdf-to-text",
    ROOT / "plugins/pdf-to-text/skills/pdf-to-text/bin/nutrient",
    ROOT / "plugins/query/skills/query/bin/query",
]

CUSTOMER_TEXT_FILES = [
    ROOT / "README.md",
    ROOT / "CHANGELOG.md",
    ROOT / "plugins/pdf-to-markdown/skills/pdf-to-markdown/SKILL.md",
    ROOT / "plugins/pdf-to-text/skills/pdf-to-text/SKILL.md",
    ROOT / "plugins/query/skills/query/SKILL.md",
]

PLUGIN_VERSIONS = {
    "pdf-to-markdown": "1.3.0",
    "pdf-to-text": "1.2.0",
    "query": "1.1.0",
}

RETIRED_PHRASES = [
    "one-time credits",
    "included credits used",
    "automatic included credits",
    "successful standard conversions use 1 credit",
    "successful vision conversions use 2",
    "vision requires a paid",
    "containers and ci require sign-in",
    "hidden no-signup access",
    "same credit pool",
]


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_shell_files() -> None:
    for shell_file in SHELL_FILES:
        subprocess.run(["sh", "-n", str(shell_file)], check=True)

    shellcheck = shutil.which("shellcheck")
    if shellcheck:
        subprocess.run([shellcheck, "-s", "sh", *map(str, SHELL_FILES)], check=True)


def check_launcher_copies() -> None:
    markdown_launcher = SHELL_FILES[1].read_text().replace(
        'exec "$SCRIPT_DIR/pdf-to-markdown"', 'exec "$SCRIPT_DIR/CONVERTER"'
    )
    text_launcher = SHELL_FILES[3].read_text().replace(
        'exec "$SCRIPT_DIR/pdf-to-text"', 'exec "$SCRIPT_DIR/CONVERTER"'
    )
    if markdown_launcher != text_launcher:
        fail("the two bundled nutrient launchers differ beyond their converter target")

    shared_wrappers = []
    for wrapper in (SHELL_FILES[0], SHELL_FILES[2], SHELL_FILES[4]):
        contents = wrapper.read_text()
        start = contents.find("# BEGIN SHARED INSTALL WRAPPER\n")
        end = contents.find("# END SHARED INSTALL WRAPPER\n")
        if start < 0 or end < 0 or end <= start:
            fail(f"{wrapper.relative_to(ROOT)} is missing shared-wrapper markers")
        shared_wrappers.append(contents[start:end])

    if len(set(shared_wrappers)) != 1:
        fail("the three bundled wrappers have drifted in their shared install logic")


def load_json(path: Path) -> dict:
    with path.open() as source:
        return json.load(source)


def check_plugin_versions() -> None:
    marketplace = load_json(ROOT / ".claude-plugin/marketplace.json")
    marketplace_versions = {
        plugin["name"]: plugin["version"] for plugin in marketplace["plugins"]
    }

    for plugin, expected in PLUGIN_VERSIONS.items():
        for manifest_name in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
            manifest = load_json(ROOT / "plugins" / plugin / manifest_name)
            if manifest["version"] != expected:
                fail(f"{plugin} {manifest_name} has version {manifest['version']}; expected {expected}")

        if marketplace_versions.get(plugin) != expected:
            fail(f"the marketplace version for {plugin} is not {expected}")


def check_customer_text() -> None:
    for path in CUSTOMER_TEXT_FILES:
        contents = path.read_text().lower()
        for phrase in RETIRED_PHRASES:
            if phrase in contents:
                fail(
                    f"retired wording remains in {path.relative_to(ROOT)}: {phrase!r}"
                )


def check_wrapper_dispatch() -> None:
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Darwin" and machine in {"arm64", "aarch64"}:
        binary_name = "nutrient-macos-arm64"
    elif system == "Linux" and machine in {"x86_64", "amd64"}:
        binary_name = "nutrient-linux-amd64"
    elif system == "Linux" and machine in {"arm64", "aarch64"}:
        binary_name = "nutrient-linux-arm64"
    else:
        print(f"Skipping wrapper dispatch test on {system}/{machine}")
        return

    with tempfile.TemporaryDirectory(prefix="nutrient-skill-test-") as directory:
        temporary = Path(directory)
        fake_binary = temporary / binary_name
        fake_binary.write_text(
            "#!/bin/sh\n"
            "if [ \"${1:-}\" = \"--version\" ]; then\n"
            "  echo 'nutrient 1.4.1'\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$(basename \"$0\")\" = \"nutrient\" ] && "
            "[ \"${1:-}\" = \"auth\" ] && [ \"${2:-}\" = \"--help\" ]; then\n"
            "  if [ \"${FAKE_ACCOUNT_COMMANDS:-1}\" = \"1\" ]; then\n"
            "    printf '  nutrient auth login\\n  nutrient auth status\\n  nutrient auth logout\\n'\n"
            "  else\n"
            "    printf 'Usage: nutrient [COMMAND]\\n'\n"
            "  fi\n"
            "  exit 0\n"
            "fi\n"
            "printf 'command=%s args=' \"$(basename \"$0\")\"\n"
            "printf '%s ' \"$@\"\n"
            "printf '\\n'\n"
        )
        fake_binary.chmod(0o755)

        archive = temporary / "release.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(fake_binary, arcname=binary_name)

        checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
        checksum_file = temporary / "release.tar.gz.sha256"
        checksum_file.write_text(f"{checksum}  {archive.name}\n")

        fake_tools = temporary / "bin"
        fake_tools.mkdir()
        fake_curl = fake_tools / "curl"
        fake_curl.write_text(
            "#!/bin/sh\n"
            "[ \"${FAKE_CDN_FAILURE:-0}\" = \"0\" ] || exit 22\n"
            "destination=''\n"
            "url=''\n"
            "while [ \"$#\" -gt 0 ]; do\n"
            "  case \"$1\" in\n"
            "    -o) destination=$2; shift 2 ;;\n"
            "    http*) url=$1; shift ;;\n"
            "    *) shift ;;\n"
            "  esac\n"
            "done\n"
            "case \"$url\" in\n"
            "  */LATEST) printf '%s\\n' \"$FAKE_RELEASE_ID\" ;;\n"
            "  *.tar.gz.sha256) cp \"$FAKE_CHECKSUM\" \"$destination\" ;;\n"
            "  *.tar.gz) cp \"$FAKE_ARCHIVE\" \"$destination\" ;;\n"
            "  *) exit 1 ;;\n"
            "esac\n"
        )
        fake_curl.chmod(0o755)

        environment = os.environ.copy()
        environment.update(
            {
                "HOME": str(temporary / "home"),
                "TMPDIR": str(temporary / "tmp"),
                "PATH": f"{fake_tools}{os.pathsep}{environment['PATH']}",
                "FAKE_RELEASE_ID": "2026-08-28T000000Z",
                "FAKE_ARCHIVE": str(archive),
                "FAKE_CHECKSUM": str(checksum_file),
            }
        )
        Path(environment["HOME"]).mkdir()
        Path(environment["TMPDIR"]).mkdir()

        cases = [
            (SHELL_FILES[0], ["input.pdf", "output.md"], "command=pdf-to-markdown"),
            (
                SHELL_FILES[0],
                ["--vision", "scan.pdf", "scan.md"],
                "command=pdf-to-markdown args=--vision scan.pdf scan.md",
            ),
            (SHELL_FILES[1], ["auth", "status"], "command=nutrient"),
            (SHELL_FILES[2], ["input.pdf", "output.txt"], "command=pdf-to-text"),
            (
                SHELL_FILES[2],
                ["--vision", "scan.pdf", "scan.json"],
                "command=pdf-to-text args=--vision scan.pdf scan.json",
            ),
            (SHELL_FILES[3], ["auth", "status"], "command=nutrient"),
            (SHELL_FILES[4], ["text", "output.md", "question"], "command=query"),
        ]
        for executable, arguments, expected in cases:
            result = subprocess.run(
                [str(executable), *arguments],
                capture_output=True,
                text=True,
                env=environment,
            )
            if result.returncode != 0:
                fail(
                    f"{executable.relative_to(ROOT)} exited {result.returncode}: "
                    f"{result.stderr.strip()}"
                )
            if expected not in result.stdout:
                fail(f"{executable.relative_to(ROOT)} did not dispatch to {expected}")

        old_cache_environment = environment.copy()
        old_cache_environment.update(
            {
                "FAKE_ACCOUNT_COMMANDS": "0",
                "FAKE_CDN_FAILURE": "1",
            }
        )
        update_required = (
            "The installed Nutrient CLI does not support account commands. "
            "Connect to the internet and retry so it can be updated."
        )
        for launcher in (SHELL_FILES[1], SHELL_FILES[3]):
            old_cache = subprocess.run(
                [str(launcher), "auth", "status"],
                capture_output=True,
                text=True,
                env=old_cache_environment,
            )
            if old_cache.returncode == 0 or update_required not in old_cache.stderr:
                fail(
                    f"{launcher.relative_to(ROOT)} accepted a conversion-only "
                    "Nutrient CLI 1.4.1 cache after a failed CDN refresh"
                )

        bad_checksum = temporary / "bad.sha256"
        bad_checksum.write_text(f"{'0' * 64}  {archive.name}\n")
        rejected_environment = environment.copy()
        rejected_environment.update(
            {
                "HOME": str(temporary / "bad-home"),
                "FAKE_CHECKSUM": str(bad_checksum),
            }
        )
        Path(rejected_environment["HOME"]).mkdir()
        rejected = subprocess.run(
            [str(SHELL_FILES[0]), "input.pdf", "output.md"],
            capture_output=True,
            text=True,
            env=rejected_environment,
        )
        if rejected.returncode == 0 or "Checksum mismatch" not in rejected.stderr:
            fail("the wrapper did not reject an archive with the wrong checksum")


def main() -> None:
    check_shell_files()
    check_launcher_copies()
    check_plugin_versions()
    check_customer_text()
    check_wrapper_dispatch()
    print("PDF CLI skills validation passed")


if __name__ == "__main__":
    main()
