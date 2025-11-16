"""CLI tests for lessons_agent."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_cli_mock_run_creates_files():
    tmp_dir = Path(tempfile.mkdtemp())
    cmd = [
        sys.executable,
        "-m",
        "lessons_agent.cli",
        "generate-lessons",
        "CLI Topic",
        "--level",
        "beginner",
        "--num-lessons",
        "1",
        "--output-dir",
        str(tmp_dir),
        "--mock-run",
    ]
    completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
    output_files = list(tmp_dir.glob("*.json"))
    assert output_files, f"No JSON files created. stdout={completed.stdout} stderr={completed.stderr}"
    index_files = [p for p in output_files if "index" in p.name]
    assert index_files, "Index file not generated"
    index_data = json.loads(index_files[0].read_text())
    assert index_data["topic"] == "CLI Topic"


if __name__ == "__main__":
    test_cli_mock_run_creates_files()
    print("CLI tests passed.")

