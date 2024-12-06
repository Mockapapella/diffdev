# src/context.py
import logging
import curses
from pathlib import Path
from typing import List, Dict, Optional, Any

from .file_selector import FileSelector

logger = logging.getLogger(__name__)


class ContextManager:
    def __init__(self):
        self.selector = FileSelector()
        self.context: List[Dict[str, Any]] = []

    def set_context_from_selector(self, selected_files: List[Dict[str, str]]) -> None:
        """Set context from files selected in the TUI."""
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
        """Get full message list for LLM including context and prompt."""
        messages = self.context.copy()
        messages.append({"role": "user", "content": prompt})
        return messages

    def select_files(self) -> Optional[List[Dict[str, str]]]:
        """Run the TUI selector and update context."""
        try:
            self.selector.load_gitignore(Path.cwd())
            self.selector.build_tree(Path.cwd())
            return curses.wrapper(self.selector.run)
        except Exception as e:
            logger.error(f"Error in file selection: {e}")
            return None
