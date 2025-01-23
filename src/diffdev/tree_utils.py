"""Directory tree management and file content formatting utilities.

This module provides utilities for generating and managing directory tree structures,
formatting file contents with line numbers, and handling project file hierarchies
while respecting gitignore rules.
"""

import logging
from pathlib import Path
from typing import List
from typing import Optional

from .gitignore import GitignoreParser

logger = logging.getLogger(__name__)


class FileContentFormatter:
    """File content formatting utility class.

    Provides static methods for formatting file contents with line numbers
    and consistent spacing for display purposes.
    """

    @staticmethod
    def format_file_content(file_path: Path) -> str:
        """Format a file's content with line numbers and consistent spacing.

        Args:
            file_path (Path): Path to the file to format.

        Returns:
            str: Formatted file content with line numbers and headers.
            For binary files, returns a [Binary file] message.
            For errors, returns an error message.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Calculate padding for line numbers based on total lines
            padding = len(str(len(lines)))

            # Format each line with padding
            formatted_lines = [
                f"{str(i + 1).rjust(padding)} | {line}" for i, line in enumerate(lines)
            ]

            separator = "-" * 80

            return f"\n{file_path}:\n{separator}\n{''.join(formatted_lines)}\n{separator}\n"

        except UnicodeDecodeError:
            return f"\n{file_path}: [Binary file]\n"
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return f"\n{file_path}: [Error reading file: {e}]\n"


class DirectoryNode:
    """Represents a node in the directory tree structure.

    Used to build and maintain a hierarchical representation of files and
    directories in the project, supporting both expanded and collapsed states
    for TUI display.

    Attributes:
        name (str): Name of the file or directory.
        is_dir (bool): Whether this node represents a directory.
        children (dict): Dictionary of child nodes (for directories).
        is_expanded (bool): Whether this directory is expanded in the TUI.
        full_path (str): Complete path from the project root.
    """

    def __init__(self, name, is_dir=True):
        """Initialize a directory node.

        Args:
            name (str): Name of the file or directory.
            is_dir (bool, optional): Whether this is a directory. Defaults to True.
        """
        self.name = name
        self.is_dir = is_dir
        self.children = {}
        self.is_expanded = False
        self.full_path = ""


class ProjectTreeGenerator:
    """Generates a visual tree representation of a project directory.

    Creates a formatted string representation of a project's directory structure,
    respecting gitignore rules and providing file content previews.

    Attributes:
        root_path (Path): Root directory of the project.
        gitignore_parser (Optional[GitignoreParser]): Parser for gitignore patterns.
        output (List[str]): Accumulated tree structure output lines.
        file_contents (List[str]): Accumulated file content previews.
        indent (str): Indentation string for tree structure.
        branch (str): Branch symbol for tree structure.
        last_branch (str): Last branch symbol for tree structure.
        pipe (str): Vertical pipe symbol for tree structure.
    """

    def __init__(self, root_path: Path, gitignore_parser: Optional[GitignoreParser] = None):
        """Initialize the project tree generator.

        Args:
            root_path (Path): Root directory to generate tree from.
            gitignore_parser (Optional[GitignoreParser], optional): Parser for
                gitignore patterns. Defaults to None.
        """
        self.root_path = root_path
        self.gitignore_parser = gitignore_parser
        self.output: List[str] = []
        self.file_contents: List[str] = []
        self.indent = "    "
        self.branch = "├── "
        self.last_branch = "└── "
        self.pipe = "│   "

    def should_skip(self, path: Path) -> bool:
        """Check if a path should be skipped based on gitignore rules.

        Args:
            path (Path): Path to check.

        Returns:
            bool: True if the path should be skipped, False otherwise.
        """
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
        """Generate the tree structure for a directory.

        Recursively builds the tree structure, adding both directories
        and files to the output with proper formatting and indentation.

        Args:
            directory (Path): Directory to process.
            prefix (str, optional): Current line prefix for formatting. Defaults to "".
        """
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
        """Generate and return the complete tree representation.

        Returns:
            str: Complete formatted tree structure including file contents.
        """
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
