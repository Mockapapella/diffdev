"""Context management module for diffdev.

This module handles the management of file contexts for the diffdev tool,
providing functionality to select, store, and format file contents for
use in LLM prompts.
"""

import curses
import logging
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from .file_selector import FileSelector

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages file context for LLM interactions.

    Handles the selection, storage, and formatting of file contents that will
    be used as context for LLM prompts. Provides methods for updating the
    context through file selection and formatting messages for the LLM.

    Attributes:
        selector (FileSelector): TUI-based file selector instance.
        context (List[Dict[str, Any]]): List of context messages for the LLM,
            where each message contains file content and metadata.
    """

    def __init__(self):
        """Initialize the context manager.

        Creates a new FileSelector instance and initializes an empty context list.
        """
        self.selector = FileSelector()
        self.context: List[Dict[str, Any]] = []

    def set_context_from_selector(self, selected_files: List[Dict[str, str]]) -> None:
        """Set context from files selected in the TUI.

        Formats the selected files' contents into the appropriate structure
        for LLM context messages.

        Args:
            selected_files: List of dictionaries containing file paths and contents.
                Each dictionary should have 'path' and 'content' keys.
        """
        self.context = []
        for file_data in selected_files:
            self.context.append(
                {
                    "role": "user",
                    "content": (
                        f"<document>\n"
                        f"<source>{file_data['path']}</source>\n"
                        f"<document_content>\n{file_data['content']}\n</document_content>\n"
                        f"</document>"
                    ),
                }
            )

    def get_messages(self, prompt: str) -> List[Dict[str, str]]:
        """Get full message list for LLM including context and prompt.

        Creates a complete message list for the LLM by combining the stored
        file context with the user's prompt.

        Args:
            prompt: User's prompt text to append to the context.

        Returns:
            List of message dictionaries containing both context and the prompt,
            formatted for the LLM.
        """
        messages = self.context.copy()
        messages.append({"role": "user", "content": prompt})
        return messages

    def select_files(self) -> Optional[List[Dict[str, str]]]:
        """Run the TUI selector to update context.

        Launches the file selector interface to allow the user to choose
        new files for the context.

        Returns:
            Optional list of dictionaries containing selected file information,
            or None if selection is cancelled or fails.
        """
        try:
            self.selector.load_gitignore(Path.cwd())
            self.selector.build_tree(Path.cwd())
            return curses.wrapper(self.selector.run)
        except Exception as e:
            logger.error(f"Error in file selection: {e}")
            return None
