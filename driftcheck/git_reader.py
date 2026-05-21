"""Reads expected configuration state from a git repository."""

import subprocess
from pathlib import Path
from typing import Optional


class GitReaderError(Exception):
    """Raised when git operations fail."""


class GitReader:
    """Reads file contents from a git repository at a specific ref."""

    def __init__(self, repo_path: str | Path, ref: str = "HEAD"):
        self.repo_path = Path(repo_path).resolve()
        self.ref = ref
        self._validate_repo()

    def _validate_repo(self) -> None:
        """Ensure the path is a valid git repository."""
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise GitReaderError(
                f"{self.repo_path} is not a valid git repository"
            )

    def read_file(self, file_path: str) -> str:
        """Read a file's content at the configured git ref."""
        result = subprocess.run(
            ["git", "show", f"{self.ref}:{file_path}"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise GitReaderError(
                f"Could not read '{file_path}' at ref '{self.ref}': {result.stderr.strip()}"
            )
        return result.stdout

    def list_files(self, pattern: Optional[str] = None) -> list[str]:
        """List tracked files at the configured git ref, optionally filtered by glob pattern."""
        cmd = ["git", "ls-tree", "-r", "--name-only", self.ref]
        if pattern:
            cmd += ["--", pattern]
        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise GitReaderError(
                f"Could not list files at ref '{self.ref}': {result.stderr.strip()}"
            )
        return [line for line in result.stdout.splitlines() if line]

    def get_commit_sha(self) -> str:
        """Return the full SHA of the current ref."""
        result = subprocess.run(
            ["git", "rev-parse", self.ref],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise GitReaderError(
                f"Could not resolve ref '{self.ref}': {result.stderr.strip()}"
            )
        return result.stdout.strip()
