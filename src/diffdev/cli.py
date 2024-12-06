# src/cli.py
import os
import sys
import logging
import curses
import fnmatch
import argparse
import subprocess
import pyperclip
from pathlib import Path
from typing import Optional, List, Dict, Any

from .config import ConfigManager
from .context import ContextManager
from .llm import LLMClient
from .patch import PatchManager
from .file_selector import FileSelector

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


class CLI:
    def __init__(self):
        self.config = ConfigManager()
        self.context = ContextManager()
        self.llm = LLMClient(self.config.get_api_key())
        self.patch_manager = PatchManager()
        self.last_patch: Optional[str] = None
        self.last_rolled_back_patch: Optional[str] = None

    def run(self) -> None:
        print("\nStarting diffdev...")
        print("Select files to include in the context:")

        selector = FileSelector()
        try:
            selector.load_gitignore(os.getcwd())
            selector.build_tree(os.getcwd())
            selected_files = curses.wrapper(selector.run)

            if not selected_files:
                print("No files selected. Exiting.")
                return

            self.context.set_context_from_selector(selected_files)
            print(f"\nInitialized context with {len(selected_files)} files.")
            print(
                "Commands: 'exit' to quit, 'select' to choose files, 'undo' to rollback, 'redo' to reapply last undone patch"
            )

        except Exception as e:
            print(f"Error in file selection: {e}")
            return

        while True:
            try:
                command = input("\nEnter command or prompt: ").strip()

                if command.lower() == "exit":
                    break

                elif command.lower() == "select":
                    selected_files = self.context.select_files()
                    if selected_files:
                        self.context.set_context_from_selector(selected_files)
                        print(f"Updated context with {len(selected_files)} files.")
                    else:
                        print("File selection cancelled or no files selected.")

                elif command.lower() == "undo":
                    if self.last_patch:
                        try:
                            self.patch_manager.rollback(self.last_patch)
                            print("Changes rolled back successfully.")
                            self.last_rolled_back_patch = self.last_patch
                            self.last_patch = None
                        except Exception as e:
                            print(f"Error rolling back changes: {e}")
                    else:
                        print("No changes to undo.")

                elif command.lower() == "redo":
                    if self.last_rolled_back_patch:
                        try:
                            self.patch_manager.apply_patch(self.last_rolled_back_patch)
                            print("Changes reapplied successfully.")
                            self.last_patch = self.last_rolled_back_patch
                            self.last_rolled_back_patch = None
                        except Exception as e:
                            print(f"Error reapplying changes: {e}")
                    else:
                        print("No changes to redo.")

                else:
                    # Treat as prompt for LLM
                    # Clear redo history when making new changes
                    self.last_rolled_back_patch = None
                    try:
                        messages = self.context.get_messages(command)
                        response = self.llm.send_prompt(
                            messages, command, self.config.get_system_prompt()
                        )

                        patch_path = self.patch_manager.generate_patch(response)
                        self.patch_manager.apply_patch(patch_path)
                        self.last_patch = patch_path
                        print("\nChanges applied successfully.")

                    except Exception as e:
                        print(f"\nError: {e}")

            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                continue

            except Exception as e:
                print(f"Error: {e}")
                continue


def copy_directory_contents(directory: Optional[str] = None) -> None:
    """Copy the contents of a directory to the clipboard"""
    try:
        # Get the target directory
        target_path = Path(directory if directory else ".").resolve()

        if not target_path.exists():
            logger.error(f"Directory not found: {target_path}")
            sys.exit(1)

        # Find the root directory (containing .git or .gitignore)
        current = target_path
        while current != current.parent:
            if (current / ".git").exists() or (current / ".gitignore").exists():
                break
            current = current.parent

        root_dir = current
        gitignore_path = root_dir / ".gitignore"

        # Initialize gitignore parser
        gitignore_parser = GitignoreParser(gitignore_path)

        # Generate the tree
        logger.info("Starting tree generation")
        generator = ProjectTreeGenerator(target_path, gitignore_parser)
        tree = generator.get_tree()

        # Copy to clipboard
        try:
            pyperclip.copy(tree)
            logger.info("Content successfully copied to clipboard")
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
            logger.info("Printing content to stdout instead...")
            print(tree)

        logger.info("Tree generation complete")

    except Exception as e:
        logger.error(f"Error copying directory contents: {e}")
        sys.exit(1)


def main():
    try:
        # Set up logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

        # Parse command line arguments
        parser = argparse.ArgumentParser(description="diffdev - AI-assisted code changes")
        parser.add_argument(
            "--copydir",
            nargs="?",
            const=".",
            help="Copy directory contents to clipboard (default: current directory)",
        )
        args = parser.parse_args()

        # Handle directory copy mode
        if args.copydir is not None:
            copy_directory_contents(args.copydir)
            return

        # Normal diffdev mode
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("Error: ANTHROPIC_API_KEY environment variable not set")
            sys.exit(1)

        cli = CLI()
        cli.run()

    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
