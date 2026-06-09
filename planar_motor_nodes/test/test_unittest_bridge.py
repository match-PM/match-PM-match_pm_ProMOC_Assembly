"""Run the existing pytest suite when colcon invokes unittest."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest


class TestPytestBridge(unittest.TestCase):
    def test_pytest_suite(self) -> None:
        if os.environ.get("PYTEST_CURRENT_TEST"):
            self.skipTest("colcon unittest bridge only")

        repo_root = Path(__file__).resolve().parents[2]
        test_dir = Path(__file__).resolve().parent

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(test_dir.relative_to(repo_root)),
                "-q",
                "--import-mode=importlib",
                "-p",
                "no:cacheprovider",
                "--ignore",
                str(Path(__file__).resolve().relative_to(repo_root)),
            ],
            cwd=repo_root,
            env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
            capture_output=True,
            text=True,
            check=False,
        )

        output = (result.stdout or "") + (result.stderr or "")
        self.assertEqual(result.returncode, 0, output)
