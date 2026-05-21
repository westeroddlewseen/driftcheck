"""Loads and parses expected configuration from YAML/JSON files in a git repo."""

import json
import yaml
from pathlib import PurePosixPath
from typing import Any

from driftcheck.git_reader import GitReader, GitReaderError


class ConfigLoaderError(Exception):
    """Raised when configuration cannot be loaded or parsed."""


class ConfigLoader:
    """Reads and parses service configuration files from a git repository."""

    SUPPORTED_EXTENSIONS = {".yaml", ".yml", ".json"}

    def __init__(self, git_reader: GitReader) -> None:
        self._reader = git_reader

    def load(self, path: str, ref: str = "HEAD") -> dict[str, Any]:
        """Load and parse a configuration file at *path* from *ref*.

        Args:
            path: Repo-relative path to the config file.
            ref:  Git ref (branch, tag, or commit SHA) to read from.

        Returns:
            Parsed configuration as a dictionary.

        Raises:
            ConfigLoaderError: If the file cannot be read or parsed.
        """
        ext = PurePosixPath(path).suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ConfigLoaderError(
                f"Unsupported file extension '{ext}'. "
                f"Expected one of {sorted(self.SUPPORTED_EXTENSIONS)}."
            )

        try:
            raw = self._reader.read_file(path, ref=ref)
        except GitReaderError as exc:
            raise ConfigLoaderError(f"Failed to read '{path}' at ref '{ref}': {exc}") from exc

        try:
            if ext == ".json":
                data = json.loads(raw)
            else:
                data = yaml.safe_load(raw)
        except (json.JSONDecodeError, yaml.YAMLError) as exc:
            raise ConfigLoaderError(f"Failed to parse '{path}': {exc}") from exc

        if not isinstance(data, dict):
            raise ConfigLoaderError(
                f"Expected a mapping at the top level of '{path}', got {type(data).__name__}."
            )

        return data
