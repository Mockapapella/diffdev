"""Command-line interface module for diffdev.

This module provides the main command-line interface for the diffdev tool,
handling user interaction, file selection, and coordinating between various
components like the LLM client, patch manager, and context manager.
"""

import argparse
import curses
import logging
import os
import sys
from typing import Optional

from .clipboard import copy_directory_contents
from .config import ConfigManager
from .context import ContextManager
from .file_selector import FileSelector
from .llm import LLMClient
from .patch import PatchManager

logger = logging.getLogger(__name__)


class CLI:
    """Main command-line interface handler for diffdev.

    Manages the interactive session with the user, coordinating file selection,
    LLM interactions, and patch application. Provides commands for selecting files,
    applying changes, and managing the undo/redo history.

    Attributes:
        config (ConfigManager): Configuration manager instance.
        context (ContextManager): Context manager for selected files.
        llm (LLMClient): Language model client instance.
        patch_manager (PatchManager): Manager for patch operations.
        last_patch (Optional[str]): Path to the last applied patch.
        last_rolled_back_patch (Optional[str]): Path to the last rolled back patch.
    """

    def __init__(self):
        """Initialize the CLI handler.

        Sets up the configuration, context management, LLM client, and patch
        management components.
        """
        self.config = ConfigManager()
        self.context = ContextManager()
        self.llm = LLMClient(self.config.get_api_key())
        self.patch_manager = PatchManager()
        self.last_patch: Optional[str] = None
        self.last_rolled_back_patch: Optional[str] = None

    def run(self) -> None:
        """Run the interactive CLI session.

        Manages the main interaction loop, handling file selection, command
        processing, and error handling. Supports commands for file selection,
        undo/redo operations, and LLM-guided code modifications.

        The following commands are supported:
        - 'exit': Quit the program
        - 'select': Choose new files for context
        - 'undo': Rollback last applied changes
        - 'redo': Reapply last rolled back changes
        - Any other input is treated as a prompt for the LLM

        Raises:
            Various exceptions may be raised and are caught internally,
            with appropriate error messages displayed to the user.
        """
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


def main():
    """Entry point for the diffdev command-line tool.

    Sets up logging, processes command-line arguments, and initializes the
    main CLI handler. Supports both normal interactive mode and directory
    copy mode.

    The following command-line options are supported:
    --copydir [PATH]: Copy directory contents to clipboard (defaults to current directory)

    Environment variables required:
    ANTHROPIC_API_KEY: API key for accessing Claude API

    Returns:
        None

    Raises:
        SystemExit: If the ANTHROPIC_API_KEY environment variable is not set.
    """
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
        parser.add_argument(
            "--patch-from-clipboard",
            action="store_true",
            help="Generate and apply a patch from clipboard contents",
        )
        parser.add_argument(
            "--apply-patch",
            type=str,
            help="Apply a patch file to the repository",
            metavar="PATCH_FILE",
        )
        parser.add_argument(
            "--undo-patch",
            type=str,
            help="Undo (reverse apply) a patch file",
            metavar="PATCH_FILE",
        )
        args = parser.parse_args()

        # Handle directory copy mode
        if args.copydir is not None:
            copy_directory_contents(args.copydir)
            return

        # Handle patch operations
        patch_manager = PatchManager()

        if args.patch_from_clipboard:
            try:
                import json

                import pyperclip

                clipboard_content = pyperclip.paste()
                patch_data = json.loads(clipboard_content)
                patch_path = patch_manager.generate_patch(patch_data)
                patch_manager.apply_patch(patch_path)
                print("Successfully applied patch from clipboard")
                return
            except json.JSONDecodeError:
                print("Error: Clipboard contents are not valid JSON")
                sys.exit(1)
            except Exception as e:
                print(f"Error applying patch from clipboard: {e}")
                sys.exit(1)

        if args.apply_patch:
            try:
                patch_manager.apply_patch(args.apply_patch)
                print(f"Successfully applied patch file: {args.apply_patch}")
                return
            except Exception as e:
                print(f"Error applying patch file: {e}")
                sys.exit(1)

        if args.undo_patch:
            try:
                patch_manager.rollback(args.undo_patch)
                print(f"Successfully undid patch file: {args.undo_patch}")
                return
            except Exception as e:
                print(f"Error undoing patch file: {e}")
                sys.exit(1)

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
