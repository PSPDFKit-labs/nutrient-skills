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
import time
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
    elif system == "Windows" and machine in {"x86_64", "amd64"}:
        binary_name = "nutrient-windows-amd64.exe"
    elif system == "Windows" and machine in {"arm64", "aarch64"}:
        binary_name = "nutrient-windows-arm64.exe"
    else:
        print(f"Skipping wrapper dispatch test on {system}/{machine}")
        return

    with tempfile.TemporaryDirectory(prefix="nutrient-skill-test-") as directory:
        temporary = Path(directory)
        fake_binary = temporary / binary_name
        if system == "Windows":
            fake_source = temporary / "fake-nutrient.cs"
            fake_source.write_text(
                "using System;\n"
                "using System.IO;\n"
                "public static class FakeNutrient {\n"
                "  public static int Main(string[] args) {\n"
                "    string command = Path.GetFileNameWithoutExtension(Environment.GetCommandLineArgs()[0]);\n"
                "    if (args.Length == 1 && args[0] == \"--version\") {\n"
                "      Console.WriteLine(\"nutrient 1.4.1\");\n"
                "      return 0;\n"
                "    }\n"
                "    if (command == \"nutrient\" && args.Length == 2 && args[0] == \"auth\" && args[1] == \"--help\") {\n"
                "      if (Environment.GetEnvironmentVariable(\"FAKE_ACCOUNT_COMMANDS\") != \"0\")\n"
                "        Console.Write(\"  nutrient auth login\\n  nutrient auth status\\n  nutrient auth logout\\n\");\n"
                "      else\n"
                "        Console.WriteLine(\"Usage: nutrient [COMMAND]\");\n"
                "      return 0;\n"
                "    }\n"
                "    Console.Write(\"command=\" + command + \" args=\");\n"
                "    foreach (string argument in args) Console.Write(argument + \" \");\n"
                "    Console.WriteLine();\n"
                "    return 0;\n"
                "  }\n"
                "}\n"
            )
            compile_environment = os.environ.copy()
            compile_environment.update(
                {
                    "FAKE_NUTRIENT_SOURCE": str(fake_source),
                    "FAKE_NUTRIENT_BINARY": str(fake_binary),
                }
            )
            subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-Command",
                    "$source = Get-Content -Raw -LiteralPath $env:FAKE_NUTRIENT_SOURCE; "
                    "Add-Type -TypeDefinition $source -Language CSharp "
                    "-OutputAssembly $env:FAKE_NUTRIENT_BINARY "
                    "-OutputType ConsoleApplication",
                ],
                check=True,
                env=compile_environment,
            )
        else:
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

        def wrapper_command(executable: Path, *arguments: str) -> list[str]:
            command = [str(executable), *arguments]
            if system == "Windows":
                command.insert(0, "sh")
            return command

        def shell_path(path: Path) -> str:
            # Git Bash accepts drive-letter paths with forward slashes. Native
            # backslashes passed through environment variables would instead be
            # treated as ordinary filename characters by the shell helpers.
            return path.as_posix() if system == "Windows" else str(path)

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
                "HOME": shell_path(temporary / "home"),
                "TMPDIR": shell_path(temporary / "tmp"),
                "PATH": f"{fake_tools}{os.pathsep}{environment['PATH']}",
                "FAKE_RELEASE_ID": "2026-08-28T000000Z",
                "FAKE_ARCHIVE": shell_path(archive),
                "FAKE_CHECKSUM": shell_path(checksum_file),
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
                wrapper_command(executable, *arguments),
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
                wrapper_command(launcher, "auth", "status"),
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
                "HOME": shell_path(temporary / "bad-home"),
                "FAKE_CHECKSUM": shell_path(bad_checksum),
            }
        )
        Path(rejected_environment["HOME"]).mkdir()
        rejected = subprocess.run(
            wrapper_command(SHELL_FILES[0], "input.pdf", "output.md"),
            capture_output=True,
            text=True,
            env=rejected_environment,
        )
        if rejected.returncode == 0 or "Checksum mismatch" not in rejected.stderr:
            fail("the wrapper did not reject an archive with the wrong checksum")

        # The cross-process swap test below intercepts native mkdir/mv paths and
        # is covered on both Unix runners. The Windows runner's job is the
        # platform-specific contract: Git Bash must install the .exe, create its
        # extensionless command link/copy, and execute every public launcher.
        if system == "Windows":
            return

        real_mkdir = shutil.which("mkdir")
        real_mv = shutil.which("mv")
        if not real_mkdir or not real_mv:
            fail("the wrapper race test requires mkdir and mv")

        race_home = temporary / "race-home"
        race_tmp = temporary / "race-tmp"
        race_home.mkdir()
        race_tmp.mkdir()
        race_environment = environment.copy()
        race_environment.update(
            {
                "HOME": str(race_home),
                "TMPDIR": str(race_tmp),
            }
        )

        primed = subprocess.run(
            wrapper_command(SHELL_FILES[0], "input.pdf", "output.md"),
            capture_output=True,
            text=True,
            env=race_environment,
        )
        if primed.returncode != 0:
            fail(f"could not prime the wrapper race test: {primed.stderr.strip()}")

        state_file = race_home / ".local/share/nutrient/pdf-to-markdown-state"
        state_file.write_text(
            "LAST_CHECKED_AT=0\n"
            "RELEASE_ID=2026-08-28T000000Z\n"
        )

        race_tools = temporary / "race-bin"
        race_tools.mkdir()
        paused_marker = temporary / "race-paused"
        waiting_marker = temporary / "race-waiting"
        continue_marker = temporary / "race-continue"
        install_dir = race_home / ".local/share/nutrient/cli"
        lock_path = race_home / ".local/share/nutrient/.install-lock"

        fake_mv = race_tools / "mv"
        fake_mv.write_text(
            "#!/bin/sh\n"
            "if [ \"$#\" -eq 2 ] && [ \"$1\" = \"$FAKE_RACE_INSTALL_DIR\" ]; then\n"
            "  case \"$2\" in\n"
            "    \"$FAKE_RACE_INSTALL_DIR\".old.*)\n"
            "      \"$FAKE_REAL_MV\" \"$@\" || exit $?\n"
            "      : > \"$FAKE_RACE_PAUSED\"\n"
            "      while [ ! -f \"$FAKE_RACE_CONTINUE\" ]; do sleep 0.05; done\n"
            "      exit 0\n"
            "      ;;\n"
            "  esac\n"
            "fi\n"
            "exec \"$FAKE_REAL_MV\" \"$@\"\n"
        )
        fake_mv.chmod(0o755)

        fake_mkdir = race_tools / "mkdir"
        fake_mkdir.write_text(
            "#!/bin/sh\n"
            "if [ \"$#\" -eq 1 ] && [ \"$1\" = \"$FAKE_RACE_LOCK_PATH\" ] && "
            "[ -f \"$FAKE_RACE_PAUSED\" ]; then\n"
            "  : > \"$FAKE_RACE_WAITING\"\n"
            "fi\n"
            "exec \"$FAKE_REAL_MKDIR\" \"$@\"\n"
        )
        fake_mkdir.chmod(0o755)

        race_environment.update(
            {
                "PATH": (
                    f"{race_tools}{os.pathsep}{fake_tools}"
                    f"{os.pathsep}{os.environ['PATH']}"
                ),
                "FAKE_RELEASE_ID": "2026-08-29T000000Z",
                "FAKE_REAL_MKDIR": real_mkdir,
                "FAKE_REAL_MV": real_mv,
                "FAKE_RACE_INSTALL_DIR": str(install_dir),
                "FAKE_RACE_LOCK_PATH": str(lock_path),
                "FAKE_RACE_PAUSED": str(paused_marker),
                "FAKE_RACE_WAITING": str(waiting_marker),
                "FAKE_RACE_CONTINUE": str(continue_marker),
            }
        )

        def wait_for_marker(marker: Path, processes: list[subprocess.Popen]) -> bool:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if marker.exists():
                    return True
                if any(process.poll() is not None for process in processes):
                    return False
                time.sleep(0.05)
            return False

        first = subprocess.Popen(
            wrapper_command(SHELL_FILES[0], "first.pdf", "first.md"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=race_environment,
        )
        second = None
        race_problem = None
        try:
            if not wait_for_marker(paused_marker, [first]):
                race_problem = "the first wrapper did not pause during the directory swap"
            else:
                second = subprocess.Popen(
                    wrapper_command(SHELL_FILES[4], "text", "output.md", "question"),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=race_environment,
                )
                if not wait_for_marker(waiting_marker, [first, second]):
                    race_problem = "the second wrapper did not wait for the install lock"
                elif install_dir.exists():
                    race_problem = (
                        "the second wrapper recreated the live install directory "
                        "while the first wrapper held the install lock"
                    )
        finally:
            continue_marker.touch()

        processes = [first] + ([second] if second else [])
        results = []
        try:
            for process in processes:
                results.append(process.communicate(timeout=30))
        except subprocess.TimeoutExpired:
            for process in processes:
                process.kill()
            for process in processes:
                process.communicate()
            fail("the concurrent wrapper race test timed out")

        if race_problem:
            details = "; ".join(
                f"exit={process.returncode}, stderr={stderr.strip()!r}"
                for process, (_, stderr) in zip(processes, results)
            )
            fail(f"{race_problem}; {details}")

        expected_dispatches = ["command=pdf-to-markdown", "command=query"]
        for process, (stdout, stderr), expected in zip(
            processes, results, expected_dispatches
        ):
            if process.returncode != 0 or expected not in stdout:
                fail(
                    "a concurrent wrapper call failed during the install swap: "
                    f"exit={process.returncode}, stdout={stdout.strip()!r}, "
                    f"stderr={stderr.strip()!r}"
                )

        installed_binary = install_dir / binary_name
        if not installed_binary.is_file() or not os.access(installed_binary, os.X_OK):
            fail("the race test did not leave the Nutrient CLI at the top level")

        nested_directories = [path for path in install_dir.iterdir() if path.is_dir()]
        install_leftovers = list(install_dir.parent.glob("cli.new.*")) + list(
            install_dir.parent.glob("cli.old.*")
        )
        if nested_directories or install_leftovers:
            fail("the race test left nested or temporary install directories behind")


def main() -> None:
    check_shell_files()
    check_launcher_copies()
    check_plugin_versions()
    check_customer_text()
    check_wrapper_dispatch()
    print("PDF CLI skills validation passed")


if __name__ == "__main__":
    main()
