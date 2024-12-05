# src/cli.py
import os
import sys
import logging
import curses
from typing import Optional

from .config import ConfigManager
from .context import ContextManager
from .llm import LLMClient
from .patch import PatchManager
from .file_selector import FileSelector

logger = logging.getLogger(__name__)


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


def main():
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("Error: ANTHROPIC_API_KEY environment variable not set")
            sys.exit(1)

        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

        cli = CLI()
        cli.run()

    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
