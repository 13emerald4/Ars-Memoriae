import subprocess
from unittest.mock import MagicMock, patch

import pytest

import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_update


def test_check_update_standalone(monkeypatch, tmp_path):
    # If no .git exists, it returns 0 cleanly
    monkeypatch.setattr(check_update, "REPO_ROOT", tmp_path)
    res = check_update.check_and_prompt_update()
    assert res == 0


def test_check_update_up_to_date(monkeypatch):
    def mock_run(cmd, *args, **kwargs):
        if cmd[1] == "--version":
            return subprocess.CompletedProcess(cmd, 0, stdout="git version 2.40.0")
        if cmd[1] == "fetch":
            return subprocess.CompletedProcess(cmd, 0)
        if cmd[1] == "rev-parse":
            return subprocess.CompletedProcess(cmd, 0, stdout="origin/main\n")
        if cmd[1] == "rev-list":
            return subprocess.CompletedProcess(cmd, 0, stdout="0\n")
        return subprocess.CompletedProcess(cmd, 0)

    with patch("subprocess.run", side_effect=mock_run):
        res = check_update.check_and_prompt_update()
        assert res == 0


def test_check_update_available_user_accepts(monkeypatch):
    def mock_run(cmd, *args, **kwargs):
        if cmd[1] == "--version":
            return subprocess.CompletedProcess(cmd, 0, stdout="git version 2.40.0")
        if cmd[1] == "fetch":
            return subprocess.CompletedProcess(cmd, 0)
        if cmd[1] == "rev-parse":
            return subprocess.CompletedProcess(cmd, 0, stdout="origin/main\n")
        if cmd[1] == "rev-list":
            return subprocess.CompletedProcess(cmd, 0, stdout="2\n")
        if cmd[1] == "log":
            return subprocess.CompletedProcess(cmd, 0, stdout="1234abc Fix bug\n5678def Add feature\n")
        if cmd[1] == "pull":
            return subprocess.CompletedProcess(cmd, 0, stdout="Fast-forward\n")
        return subprocess.CompletedProcess(cmd, 0)

    with patch("subprocess.run", side_effect=mock_run), \
         patch("sys.stdin.isatty", return_value=True), \
         patch("builtins.input", return_value="y"):
        res = check_update.check_and_prompt_update()
        assert res == 10  # Exit code 10 signals update pulled successfully


def test_check_update_available_user_declines(monkeypatch):
    def mock_run(cmd, *args, **kwargs):
        if cmd[1] == "--version":
            return subprocess.CompletedProcess(cmd, 0, stdout="git version 2.40.0")
        if cmd[1] == "fetch":
            return subprocess.CompletedProcess(cmd, 0)
        if cmd[1] == "rev-parse":
            return subprocess.CompletedProcess(cmd, 0, stdout="origin/main\n")
        if cmd[1] == "rev-list":
            return subprocess.CompletedProcess(cmd, 0, stdout="1\n")
        if cmd[1] == "log":
            return subprocess.CompletedProcess(cmd, 0, stdout="1234abc Fix bug\n")
        return subprocess.CompletedProcess(cmd, 0)

    with patch("subprocess.run", side_effect=mock_run), \
         patch("sys.stdin.isatty", return_value=True), \
         patch("builtins.input", return_value="n"):
        res = check_update.check_and_prompt_update()
        assert res == 0  # Exit code 0 means continue without update
