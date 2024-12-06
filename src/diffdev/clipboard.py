import logging
import pyperclip
from pathlib import Path
from typing import Optional

from .tree_utils import ProjectTreeGenerator
from .gitignore import GitignoreParser

logger = logging.getLogger(__name__)


def copy_directory_contents(directory: Optional[str] = None) -> None:
    """Copy the contents of a directory to the clipboard"""
    try:
        # Get the target directory
        target_path = Path(directory if directory else ".").resolve()

        if not target_path.exists():
            logger.error(f"Directory not found: {target_path}")
            raise ValueError(f"Directory not found: {target_path}")

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
        raise
