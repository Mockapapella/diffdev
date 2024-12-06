# src/tree_utils.py
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
import os
import fnmatch
from .gitignore import GitignoreParser

logger = logging.getLogger(__name__)


class FileContentFormatter:
    """Formats file contents with line numbers"""

    @staticmethod
    def format_file_content(file_path: Path) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Calculate padding for line numbers based on total lines
            padding = len(str(len(lines)))

            # Format each line with padding
            formatted_lines = [
                f"{str(i+1).rjust(padding)} | {line}" for i, line in enumerate(lines)
            ]

            separator = "-" * 80

            return (
                f"\n{file_path}:\n"
                f"{separator}\n"
                f"{''.join(formatted_lines)}\n"
                f"{separator}\n"
            )

        except UnicodeDecodeError:
            return f"\n{file_path}: [Binary file]\n"
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return f"\n{file_path}: [Error reading file: {e}]\n"


class DirectoryNode:
    def __init__(self, name, is_dir=True):
        self.name = name
        self.is_dir = is_dir
        self.children = {}
        self.is_expanded = False
        self.full_path = ""


class ProjectTreeGenerator:
    """Generates a visual tree representation of a project directory"""

    def __init__(self, root_path: Path, gitignore_parser: Optional[GitignoreParser] = None):
        self.root_path = root_path
        self.gitignore_parser = gitignore_parser
        self.output: List[str] = []
        self.file_contents: List[str] = []
        self.indent = "    "
        self.branch = "├── "
        self.last_branch = "└── "
        self.pipe = "│   "

    def should_skip(self, path: Path) -> bool:
        if path.name == ".git":
            logger.debug(f"Ignoring {path} (.git directory)")
            return True

        if self.gitignore_parser and self.gitignore_parser.should_ignore(
            str(path.relative_to(self.root_path))
        ):
            logger.debug(f"Ignoring {path} (matches .gitignore pattern)")
            return True
        return False

    def generate_tree(self, directory: Path, prefix: str = "") -> None:
        try:
            entries = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            logger.warning(f"Permission denied: {directory}")
            return
        except Exception as e:
            logger.error(f"Error accessing directory {directory}: {e}")
            return

        entries = [e for e in entries if not self.should_skip(e)]

        for i, entry in enumerate(entries):
            is_last_entry = i == len(entries) - 1
            current_prefix = prefix + (self.last_branch if is_last_entry else self.branch)

            self.output.append(f"{current_prefix}{entry.name}")

            if entry.is_file():
                self.file_contents.append(FileContentFormatter.format_file_content(entry))

            if entry.is_dir():
                next_prefix = prefix + (self.indent if is_last_entry else self.pipe)
                self.generate_tree(entry, next_prefix)

    def get_tree(self) -> str:
        self.output = []
        self.file_contents = []
        logger.info(f"Generating tree for {self.root_path}")
        self.generate_tree(self.root_path)

        full_output = [
            "\nFile Tree:",
            "\n".join(self.output),
            "\nFile Contents:",
            "".join(self.file_contents),
        ]

        return "\n".join(full_output)
