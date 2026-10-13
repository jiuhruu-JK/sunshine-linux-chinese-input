from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MOCK_TOOL = r"""
import json
import os
import sys
from pathlib import Path

name = Path(sys.argv[0]).name
args = sys.argv[1:]
with Path(os.environ["MOCK_COMMAND_LOG"]).open("a", encoding="utf-8") as stream:
    entry = {
        "tool": name,
        "args": args,
    }
    stream.write(f"{json.dumps(entry)}\n")
if name == "conda" and args[0] == "run":
    command = args[4:]
    if command[:2] == [
        "python",
        "-c",
    ]:
        print(os.environ["MOCK_CONDA_PYTHON"])
    else:
        os.execvp(command[0], command)
elif name == "uv" and args[0] == "export":
    output = Path(args[args.index("--output-file") + 1])
    output.write_text("example-runtime==1.0\nexample-docs==1.0\n", encoding="utf-8")
elif name == "uv" and args[-2:] == [
    "dockle",
    "build",
]:
    output = Path("_site")
    output.mkdir()
    (output / "index.html").write_text("built portal", encoding="utf-8")
"""


@unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "Read the Docs runs Bash on Linux")
class ReadTheDocsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / "consumer project"
        self.project.mkdir()
        self.dockle = self.root / "shared dockle"
        self.dockle.mkdir()
        self.script = self.dockle / "readthedocs_build.sh"
        self.script.write_text(
            (PROJECT_ROOT / "readthedocs_build.sh").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        self.environment_file = self.dockle / "environment.yml"
        self.environment_file.write_text("name: shared-docs\n", encoding="utf-8")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name in (
            "conda",
            "uv",
            "npm",
        ):
            tool = self.bin / name
            tool.write_text(f"#!{sys.executable}\n{MOCK_TOOL}", encoding="utf-8")
            tool.chmod(0o755)
        (self.bin / "python").symlink_to(sys.executable)
        self.log = self.root / "commands.jsonl"
        self.output = self.root / "hosted output"
        self.conda_python = "/shared-conda/bin/python"

    def run_build(self, *, framework: str = "sphinx", pyproject: str = "") -> list[dict]:
        (self.project / "dockle.toml").write_text(
            f'[[targets]]\nframework = "{framework}"\n',
            encoding="utf-8",
        )
        if pyproject:
            (self.project / "pyproject.toml").write_text(pyproject, encoding="utf-8")
        environment = {
            **os.environ,
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "DOCKLE_DIR": str(self.dockle),
            "READTHEDOCS_VERSION": "600",
            "READTHEDOCS_OUTPUT": f"{self.output}/",
            "MOCK_COMMAND_LOG": str(self.log),
            "MOCK_CONDA_PYTHON": self.conda_python,
        }
        result = subprocess.run(
            [
                "bash",
                str(self.script),
            ],
            cwd=self.project,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"{result.stdout}\n{result.stderr}")
        self.assertEqual((self.output / "html/index.html").read_text(), "built portal")
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def uv_command(self, commands: list[dict], action: str) -> list[str]:
        return next(command["args"] for command in commands if command["tool"] == "uv" and command["args"][0] == action)

    def assert_docs_overlay(self, commands: list[dict], selection: list[str]) -> None:
        export = self.uv_command(commands, "export")
        self.assertIn("--locked", export)
        self.assertIn("--no-dev", export)
        self.assertNotIn("--only-group", export)  # Autodoc also needs the runtime imports.
        self.assertIn("--no-emit-project", export)
        self.assertEqual(export[export.index("--no-emit-package") + 1], "lizardbyte-dockle")
        for option in selection:
            self.assertEqual(export[export.index(option) + 1], "docs")
        install = self.uv_command(commands, "pip")
        self.assertEqual(install[1], "install")
        self.assertEqual(install[install.index("--python") + 1], str(self.dockle / ".venv/bin/python"))
        self.assertEqual(install[install.index("--requirement") + 1], export[export.index("--output-file") + 1])
        self.assertFalse(Path(export[export.index("--output-file") + 1]).exists())
        self.assertEqual(sum(command["tool"] == "uv" and command["args"][0] == "sync" for command in commands), 1)
        for command in commands:
            if command["tool"] == "uv" and command["args"][0] == "run":
                self.assertIn("--no-sync", command["args"])  # Preserve the installed consumer dependencies.

    def test_doxygen_binds_shared_conda_python_and_installs_docs_extra(self) -> None:
        docs = self.project / "docs"
        docs.mkdir()
        (docs / "environment.yml").write_text("name: unused-consumer-env\n", encoding="utf-8")
        commands = self.run_build(
            framework="doxygen",
            pyproject='[project.optional-dependencies]\ndocs = ["example-docs==1.0"]\n',
        )
        create = next(command["args"] for command in commands if command["tool"] == "conda")
        self.assertEqual(create[:2], [
            "env",
            "create",
        ])
        self.assertEqual(create[create.index("--file") + 1], str(self.environment_file))
        sync = self.uv_command(commands, "sync")
        self.assertEqual(sync[sync.index("--python") + 1], self.conda_python)
        export = self.uv_command(commands, "export")
        self.assertEqual(export[export.index("--python") + 1], self.conda_python)
        self.assert_docs_overlay(commands, ["--extra"])

    def test_docs_group_uses_hosted_python_without_creating_conda_environment(self) -> None:
        commands = self.run_build(pyproject='[dependency-groups]\ndocs = ["example-docs==1.0"]\n')
        self.assertFalse(any(command["tool"] == "conda" for command in commands))
        sync = self.uv_command(commands, "sync")
        self.assertTrue(Path(sync[sync.index("--python") + 1]).samefile(self.bin / "python"))
        self.assert_docs_overlay(commands, ["--group"])

    def test_docs_group_and_extra_are_both_installed(self) -> None:
        commands = self.run_build(pyproject="""
[dependency-groups]
docs = ["group-docs==1.0"]
[project.optional-dependencies]
docs = ["extra-docs==1.0"]
""")
        self.assert_docs_overlay(
            commands,
            [
                "--group",
                "--extra",
            ],
        )

    def test_legacy_requirements_are_installed_when_docs_selection_is_absent(self) -> None:
        docs = self.project / "docs"
        docs.mkdir()
        (docs / "requirements.txt").write_text("legacy-docs==1.0\n", encoding="utf-8")
        commands = self.run_build()
        self.assertFalse(any(command["tool"] == "uv" and command["args"][0] == "export" for command in commands))
        install = self.uv_command(commands, "pip")
        self.assertEqual(install[install.index("--requirement") + 1], "docs/requirements.txt")

    def test_no_python_project_or_requirements_still_builds(self) -> None:
        commands = self.run_build()
        self.assertFalse(any(
            command["tool"] == "uv" and command["args"][0] in {
                "export",
                "pip",
            }
            for command in commands
        ))
