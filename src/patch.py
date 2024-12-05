# src/patch.py
import logging
import subprocess
from pathlib import Path
from difflib import unified_diff
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class PatchManager:
    """Manages generation and application of patches from LLM responses."""

    def __init__(self, patch_dir: Optional[Path] = None):
        """
        Args:
            patch_dir: Directory to store patches. Defaults to current directory
        """
        self.patch_dir = Path(patch_dir) if patch_dir else Path(".")
        self.patch_dir.mkdir(exist_ok=True)

    def generate_patch(self, response: Dict[str, Any]) -> str:
        """
        Generate a patch file from LLM response.

        Args:
            response: JSON response from LLM containing file changes

        Returns:
            Path to generated patch file

        Raises:
            ValueError: If response format is invalid
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
        """
        Apply a patch file using git apply.

        Args:
            patch_path: Path to patch file

        Raises:
            subprocess.CalledProcessError: If patch application fails
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
        """
        Rollback a previously applied patch.

        Args:
            patch_path: Path to patch file to reverse

        Raises:
            subprocess.CalledProcessError: If rollback fails
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
        """
        Read a file's content.

        Args:
            filename: Path to file

        Returns:
            File content as string. Empty string if file doesn't exist.
        """
        try:
            path = Path(filename)
            if path.exists():
                return path.read_text()
            return ""
        except Exception as e:
            logger.error(f"Error reading {filename}: {e}")
            raise
