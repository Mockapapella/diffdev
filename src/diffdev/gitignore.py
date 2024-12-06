import logging
from pathlib import Path
from typing import List
import os
import fnmatch


logger = logging.getLogger(__name__)


class GitignoreParser:
    """Parser for .gitignore patterns"""

    def __init__(self, gitignore_path: Path):
        self.patterns: List[str] = []
        self.load_patterns(gitignore_path)

    def load_patterns(self, gitignore_path: Path) -> None:
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
        for pattern in self.patterns:
            if pattern.endswith("/"):
                pattern = pattern[:-1]
            if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern):
                return True
        return False
