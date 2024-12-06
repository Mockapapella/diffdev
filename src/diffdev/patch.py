"""Patch management module for diffdev.

This module handles the generation and application of git patches for code
modifications. It processes LLM responses into valid patch files and manages
their application and rollback using git commands.
"""

import logging
import subprocess
from difflib import unified_diff
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Optional

logger = logging.getLogger(__name__)


class PatchManager:
    """Manages generation and application of patches from LLM responses.

    Handles the creation of git-compatible patch files from LLM-generated
    code modifications, as well as their application and rollback. Supports
    both adding new files and modifying existing ones.

    Attributes:
        patch_dir (Path): Directory where generated patch files are stored.
    """

    def __init__(self, patch_dir: Optional[Path] = None):
        """Initialize the patch manager.

        Args:
            patch_dir (Optional[Path]): Directory to store patches. If None,
                uses the current directory.
        """
        self.patch_dir = Path(patch_dir) if patch_dir else Path(".")
        self.patch_dir.mkdir(exist_ok=True)

    def generate_patch(self, response: Dict[str, Any]) -> str:
        """Generate a patch file from LLM response.

        Creates a unified diff patch file from the code modifications specified
        in the LLM's response. Handles both file modifications and new file
        creation.

        Args:
            response (Dict[str, Any]): JSON response from LLM containing file
                changes. Expected format:
                {
                    "files": [
                        {
                            "filename": "path/to/file",
                            "changes": [
                                {
                                    "search": ["lines", "to find"],
                                    "replace": ["new", "lines"]
                                }
                            ]
                        }
                    ]
                }

        Returns:
            str: Path to the generated patch file.

        Raises:
            ValueError: If response format is invalid or files cannot be processed.
        """
        if "files" not in response:
            raise ValueError("Invalid response format: missing 'files' key")

        all_patches = []
        missing_files = []

        for file in response["files"]:
            try:
                filename = file["filename"]
                original_content = self._read_file(filename)
                new_content = original_content

                for change in file["changes"]:
                    original = "\n".join(change["search"])
                    replacement = "\n".join(change["replace"])

                    # If both file and search are empty, treat as new file
                    if not original_content and not original:
                        new_content = replacement + "\n"
                        continue

                    # If search is empty, just append replacement lines
                    if not original:
                        if not new_content.endswith("\n") and new_content:
                            new_content += "\n"
                        new_content += replacement + "\n"
                        continue

                    # If search is found, replace
                    if original in new_content:
                        new_content = new_content.replace(original, replacement)
                    else:
                        logger.warning(f"Pattern not found in {filename}")

                # Add trailing newlines only if content is non-empty
                if new_content and not new_content.endswith("\n"):
                    new_content += "\n"
                if original_content and not original_content.endswith("\n"):
                    original_content += "\n"

                # If content changed, create a diff
                if new_content != original_content:
                    patch = unified_diff(
                        original_content.splitlines(keepends=True),
                        new_content.splitlines(keepends=True),
                        fromfile=f"a/{filename}",
                        tofile=f"b/{filename}",
                    )
                    patch_list = list(patch)
                    all_patches.extend(patch_list)
                else:
                    logger.info(f"No changes needed in {filename}")

            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")
                missing_files.append(filename)
                continue

        if missing_files:
            error_msg = f"Failed to process files: {', '.join(missing_files)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        patch_path = self.patch_dir / "changes.patch"
        patch_content = "".join(all_patches)
        patch_path.write_text(patch_content)

        return str(patch_path)

    def apply_patch(self, patch_path: str) -> None:
        """Apply a patch file using git apply.

        Applies the specified patch file to the working directory using
        git's patch application functionality.

        Args:
            patch_path (str): Path to the patch file to apply.

        Raises:
            subprocess.CalledProcessError: If patch application fails.
        """
        try:
            subprocess.run(
                ["git", "apply", patch_path],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info("Successfully applied patch")

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to apply patch: {e.stderr}")
            raise

    def rollback(self, patch_path: str) -> None:
        """Rollback a previously applied patch.

        Reverses a previously applied patch using git's reverse patch
        functionality.

        Args:
            patch_path (str): Path to the patch file to reverse.

        Raises:
            subprocess.CalledProcessError: If rollback fails.
        """
        try:
            subprocess.run(
                ["git", "apply", "--reverse", patch_path],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info("Successfully rolled back patch")

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to rollback patch: {e.stderr}")
            raise

    def _read_file(self, filename: str) -> str:
        """Read a file's content.

        Reads and returns the content of the specified file. Returns an
        empty string if the file doesn't exist, allowing for new file
        creation.

        Args:
            filename (str): Path to the file to read.

        Returns:
            str: File content as string. Empty string if file doesn't exist.

        Raises:
            Exception: If file read operation fails for an existing file.
        """
        try:
            path = Path(filename)
            if path.exists():
                return path.read_text()
            return ""
        except Exception as e:
            logger.error(f"Error reading {filename}: {e}")
            raise
