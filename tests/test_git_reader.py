"""Tests for the GitReader module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from driftcheck.git_reader import GitReader, GitReaderError


REPO_PATH = "/fake/repo"


def _make_completed(returncode: int, stdout: str = "", stderr: str = ""):
    """Create a mock CompletedProcess-like object for subprocess.run."""
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


@patch("subprocess.run")
def test_init_valid_repo(mock_run):
    mock_run.return_value = _make_completed(0, stdout=".git")
    reader = GitReader(REPO_PATH)
    assert reader.ref == "HEAD"
    assert reader.repo_path == Path(REPO_PATH).resolve()


@patch("subprocess.run")
def test_init_invalid_repo_raises(mock_run):
    mock_run.return_value = _make_completed(128, stderr="not a git repo")
    with pytest.raises(GitReaderError, match="not a valid git repository"):
        GitReader(REPO_PATH)


@patch("subprocess.run")
def test_read_file_success(mock_run):
    mock_run.side_effect = [
        _make_completed(0, stdout=".git"),
        _make_completed(0, stdout="key: value\n"),
    ]
    reader = GitReader(REPO_PATH)
    content = reader.read_file("config/app.yaml")
    assert content == "key: value\n"


@patch("subprocess.run")
def test_read_file_not_found_raises(mock_run):
    mock_run.side_effect = [
        _make_completed(0, stdout=".git"),
        _make_completed(128, stderr="path not in tree"),
    ]
    reader = GitReader(REPO_PATH)
    with pytest.raises(GitReaderError, match="Could not read"):
        reader.read_file("missing.yaml")


@patch("subprocess.run")
def test_list_files_returns_paths(mock_run):
    file_list = "config/app.yaml\nconfig/db.yaml\n"
    mock_run.side_effect = [
        _make_completed(0, stdout=".git"),
        _make_completed(0, stdout=file_list),
    ]
    reader = GitReader(REPO_PATH)
    files = reader.list_files()
    assert files == ["config/app.yaml", "config/db.yaml"]


@patch("subprocess.run")
def test_list_files_with_prefix(mock_run):
    """Test that list_files correctly filters by a path prefix."""
    file_list = "config/app.yaml\nconfig/db.yaml\n"
    mock_run.side_effect = [
        _make_completed(0, stdout=".git"),
        _make_completed(0, stdout=file_list),
    ]
    reader = GitReader(REPO_PATH)
    files = reader.list_files(prefix="config/")
    assert all(f.startswith("config/") for f in files)


@patch("subprocess.run")
def test_get_commit_sha(mock_run):
    sha = "abc123def456" * 3  # 36-char fake SHA
    mock_run.side_effect = [
        _make_completed(0, stdout=".git"),
        _make_completed(0, stdout=sha + "\n"),
    ]
    reader = GitReader(REPO_PATH)
    assert reader.get_commit_sha() == sha


@patch("subprocess.run")
def test_custom_ref(mock_run):
    mock_run.return_value = _make_completed(0, stdout=".git")
    reader = GitReader(REPO_PATH, ref="main")
    assert reader.ref == "main"
