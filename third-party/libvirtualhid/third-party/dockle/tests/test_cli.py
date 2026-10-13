from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dockle import __version__
from dockle.cli import main


class CliTests(unittest.TestCase):
    def test_version_uses_package_metadata(self) -> None:
        output = io.StringIO()

        with (
            contextlib.redirect_stdout(output),
            self.assertRaises(SystemExit) as exit_status,
        ):
            main(["--version"])

        self.assertEqual(exit_status.exception.code, 0)
        self.assertEqual(output.getvalue().strip(), f"dockle {__version__}")

    def test_cmake_dir_points_to_packaged_module(self) -> None:
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            status = main(["cmake-dir"])

        directory = Path(output.getvalue().strip())
        self.assertEqual(status, 0)
        self.assertTrue((directory / "Dockle.cmake").is_file())

    def test_dry_run_does_not_create_build_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            config = root / "dockle.toml"
            config.write_text(
                """
[project]
name = "Example"

[[targets]]
name = "docs"
framework = "sphinx"
source = "docs"
""",
                encoding="utf-8",
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                status = main(["--config", str(config), "build", "--dry-run"])

            self.assertEqual(status, 0)
            self.assertIn("sphinx-build", output.getvalue())
            self.assertFalse((root / ".dockle").exists())
            self.assertFalse((root / "_site").exists())

    def test_unknown_target_is_reported_as_configuration_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "dockle.toml"
            config.write_text(
                """
[project]
name = "Example"

[[targets]]
name = "docs"
framework = "sphinx"
source = "docs"
""",
                encoding="utf-8",
            )
            error = io.StringIO()

            with contextlib.redirect_stderr(error):
                status = main(
                    ["--config", str(config), "build", "missing", "--dry-run"]
                )

            self.assertEqual(status, 2)
            self.assertIn("unknown target", error.getvalue())

    def test_internal_sphinx_runner_forwards_arguments(self) -> None:
        with patch("sphinx.cmd.build.main", return_value=0) as sphinx_main:
            status = main(["_run-sphinx", "-b", "html", "docs", "site"])

        self.assertEqual(status, 0)
        sphinx_main.assert_called_once_with(
            ["-b", "html", "docs", "site"]
        )

    def test_internal_mkdocs_runner_forwards_arguments(self) -> None:
        with patch("mkdocs.__main__.cli.main", return_value=None) as mkdocs_main:
            status = main(["_run-mkdocs", "build", "--strict"])

        self.assertEqual(status, 0)
        mkdocs_main.assert_called_once_with(
            args=["build", "--strict"],
            prog_name="mkdocs",
            standalone_mode=False,
        )


if __name__ == "__main__":
    unittest.main()
