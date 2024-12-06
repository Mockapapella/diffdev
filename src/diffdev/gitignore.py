"""Gitignore pattern matching and file filtering module.

This module provides functionality for parsing and applying gitignore patterns
to filter files and directories in the project. It supports standard gitignore
pattern syntax and provides efficient pattern matching capabilities.
"""

import fnmatch
import logging
import os
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class GitignoreParser:
    """Parses and applies gitignore patterns to filter files.

    Handles loading and parsing of .gitignore files, providing pattern matching
    functionality to determine which files and directories should be excluded
    from operations.

    Attributes:
        patterns (List[str]): List of loaded gitignore patterns.
    """

    def __init__(self, gitignore_path: Path):
        """Initialize the gitignore parser.

        Args:
            gitignore_path (Path): Path to the .gitignore file to parse.
        """
        self.patterns: List[str] = []
        self.load_patterns(gitignore_path)

    def load_patterns(self, gitignore_path: Path) -> None:
        """Load patterns from a gitignore file.

        Reads and parses patterns from the specified .gitignore file,
        storing them for later use. Comments and empty lines are ignored.

        Args:
            gitignore_path (Path): Path to the .gitignore file.
        """
        if not gitignore_path.exists():
            logger.warning(f".gitignore not found at {gitignore_path}")
            return

        logger.info(f"Loading .gitignore from {gitignore_path}")
        with open(gitignore_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    self.patterns.append(line)

    def should_ignore(self, path: str) -> bool:
        """Check if a path matches any gitignore pattern.

        Tests the given path against all loaded gitignore patterns to
        determine if it should be excluded.

        Args:
            path (str): Path to check against gitignore patterns.

        Returns:
            bool: True if the path matches any gitignore pattern and should
                be ignored, False otherwise.
        """
        for pattern in self.patterns:
            if pattern.endswith("/"):
                pattern = pattern[:-1]
            if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern):
                return True
        return False
