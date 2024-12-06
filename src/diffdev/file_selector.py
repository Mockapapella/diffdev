import curses
import logging
import pathspec
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

logger = logging.getLogger(__name__)

DEFAULT_EXCLUDES = [
    ".git/",
    "__pycache__/",
    ".venv/",
    "node_modules/",
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dylib",
    "*.egg-info/",
    ".env",
    "venv/",
    "mediafiles/",
    "staticfiles/",
    "htmlcov/",
    "data/",
    "coverage/",
    "dist/",
    "build/",
]


def debug_print(*args, **kwargs):
    """Print to a debug file since we can't use print during curses"""
    with open("context_selector_debug.log", "a") as f:
        print(*args, **kwargs, file=f)


class DirectoryNode:
    def __init__(self, name, is_dir=True):
        self.name = name
        self.is_dir = is_dir
        self.children = {}
        self.is_expanded = False
        self.full_path = ""


class FileSelector:
    """TUI-based file selection interface."""

    def __init__(self):
        self.tree = DirectoryNode("")
        self.files = []
        self.selected = set()
        self.current_pos = 0
        self.start_display = 0
        self.spec = None
        self.flat_tree = []

        # Initialize debug log
        with open("context_selector_debug.log", "w") as f:
            f.write("Starting new session\n")

    def load_gitignore(self, directory):
        """Load .gitignore patterns and combine with defaults"""
        gitignore_path = Path(directory) / ".gitignore"
        combined_patterns = DEFAULT_EXCLUDES.copy()

        if gitignore_path.is_file():
            try:
                with open(gitignore_path, "r") as f:
                    patterns = [
                        line.strip()
                        for line in f.read().splitlines()
                        if line.strip() and not line.strip().startswith("#")
                    ]
                    cleaned_patterns = []
                    for pattern in patterns:
                        if pattern in cleaned_patterns or pattern in combined_patterns:
                            continue
                        if not pattern.endswith("/") and not pattern.endswith(".*"):
                            if "*" not in pattern and "." not in pattern:
                                pattern += "/"
                        cleaned_patterns.append(pattern)
                    combined_patterns.extend(cleaned_patterns)
            except Exception as e:
                debug_print(f"Warning: Could not read .gitignore file: {e}")

        combined_patterns = list(dict.fromkeys(combined_patterns))
        self.spec = pathspec.PathSpec.from_lines("gitwildmatch", combined_patterns)

    def should_include_file(self, path, root_path):
        """Determine if a file should be included based on patterns"""
        try:
            relative_path = path.relative_to(root_path)
            is_excluded = self.spec.match_file(str(relative_path))
            return not is_excluded
        except ValueError:
            debug_print(f"Error: Could not make path relative: {path}")
            return False

    def build_tree(self, directory):
        """Build directory tree structure"""
        root_path = Path(directory).resolve()

        # First pass: collect all directories
        directories = set()
        files_found = False

        for path in root_path.rglob("*"):
            try:
                if path.is_file() and self.should_include_file(path, root_path):
                    files_found = True
                    rel_parents = [
                        p for p in path.parents if p != root_path and root_path in p.parents
                    ]
                    directories.update(p.relative_to(root_path) for p in rel_parents)
            except Exception as e:
                debug_print(f"Error processing path {path}: {e}")
                continue

        # Create directory nodes
        for dir_path in sorted(directories):
            current = self.tree
            for part in dir_path.parts:
                if part not in current.children:
                    node = DirectoryNode(part)
                    node.full_path = str(dir_path)
                    current.children[part] = node
                current = current.children[part]

        # Second pass: add files
        for path in root_path.rglob("*"):
            try:
                if path.is_file() and self.should_include_file(path, root_path):
                    relative_path = path.relative_to(root_path)
                    parts = relative_path.parts
                    current = self.tree

                    # Navigate to parent directory
                    for part in parts[:-1]:
                        if part not in current.children:
                            node = DirectoryNode(part)
                            node.full_path = str(Path(*parts[:-1]))
                            current.children[part] = node
                        current = current.children[part]

                    # Add file
                    file_node = DirectoryNode(parts[-1], is_dir=False)
                    file_node.full_path = str(relative_path)
                    current.children[parts[-1]] = file_node

                    self.files.append(
                        {
                            "path": str(relative_path),
                            "full_path": str(path),
                            "size": path.stat().st_size,
                        }
                    )
            except Exception as e:
                debug_print(f"Error adding file {path}: {e}")
                continue

        if not files_found:
            raise ValueError("No files found in directory (all files may be excluded by gitignore)")

        # Expand root level by default
        for node in self.tree.children.values():
            node.is_expanded = False
        self.update_flat_tree()

    def update_flat_tree(self):
        """Create flat representation of visible tree items"""
        self.flat_tree = []

        def traverse(node, depth=0):
            if not node.name:  # Root node
                for child in sorted(node.children.values(), key=lambda x: (not x.is_dir, x.name)):
                    traverse(child, depth)
                return

            self.flat_tree.append(
                {
                    "node": node,
                    "depth": depth,
                    "display": (
                        "+"
                        if node.is_dir and not node.is_expanded
                        else "-"
                        if node.is_dir and node.is_expanded
                        else " "
                    )
                    + " " * (depth * 2)
                    + node.name,
                }
            )

            if node.is_dir and node.is_expanded:
                for child in sorted(node.children.values(), key=lambda x: (not x.is_dir, x.name)):
                    traverse(child, depth + 1)

        traverse(self.tree)

    def run(self, stdscr):
        """Main TUI loop"""
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)

        while True:
            stdscr.clear()
            height, width = stdscr.getmaxyx()

            # Header
            header = "File Selector (Space: select, Tab: expand/collapse, Enter: confirm, q: quit)"
            stdscr.addstr(0, 0, header[: width - 1])
            stdscr.addstr(1, 0, "=" * (width - 1))

            # File list
            display_height = height - 5
            for idx in range(display_height):
                list_idx = idx + self.start_display
                if list_idx >= len(self.flat_tree):
                    break

                item = self.flat_tree[list_idx]
                node = item["node"]
                is_selected = node.full_path in self.selected

                if list_idx == self.current_pos:
                    stdscr.attron(curses.color_pair(2))
                elif node.is_dir:
                    stdscr.attron(curses.color_pair(3))

                prefix = "[*]" if is_selected else "[ ]"
                display_str = f"{prefix} {item['display']}"
                if len(display_str) > width - 1:
                    display_str = display_str[: width - 4] + "..."

                stdscr.addstr(idx + 2, 0, display_str + " " * (width - len(display_str) - 1))

                if list_idx == self.current_pos:
                    stdscr.attroff(curses.color_pair(2))
                elif node.is_dir:
                    stdscr.attroff(curses.color_pair(3))

            # Footer
            footer = f"Selected: {len(self.selected)} files"
            stdscr.addstr(height - 2, 0, "=" * (width - 1))
            stdscr.addstr(height - 1, 0, footer[: width - 1])

            stdscr.refresh()

            try:
                key = stdscr.getch()
            except KeyboardInterrupt:
                return None

            if key == ord("q"):
                return None
            elif key == ord(" "):  # Space to select
                if self.current_pos < len(self.flat_tree):
                    current_node = self.flat_tree[self.current_pos]["node"]
                    if current_node.is_dir:
                        self._toggle_directory_selection(current_node)
                    else:
                        if current_node.full_path in self.selected:
                            self.selected.remove(current_node.full_path)
                        else:
                            self.selected.add(current_node.full_path)
            elif key == ord("\t"):  # Tab to expand/collapse
                if self.current_pos < len(self.flat_tree):
                    current_node = self.flat_tree[self.current_pos]["node"]
                    if current_node.is_dir:
                        current_node.is_expanded = not current_node.is_expanded
                        self.update_flat_tree()
            elif key == curses.KEY_UP and self.current_pos > 0:
                self.current_pos -= 1
                if self.current_pos < self.start_display:
                    self.start_display = self.current_pos
            elif key == curses.KEY_DOWN and self.current_pos < len(self.flat_tree) - 1:
                self.current_pos += 1
                if self.current_pos >= self.start_display + display_height:
                    self.start_display = self.current_pos - display_height + 1
            elif key == ord("\n"):  # Enter to confirm
                return self.prepare_context()

    def _toggle_directory_selection(self, node):
        """Toggle selection for all files in a directory"""

        def collect_files(node, files):
            if not node.is_dir:
                files.add(node.full_path)
            for child in node.children.values():
                collect_files(child, files)

        dir_files = set()
        collect_files(node, dir_files)

        if any(f in self.selected for f in dir_files):
            self.selected.difference_update(dir_files)
        else:
            self.selected.update(dir_files)

    def prepare_context(self):
        """Prepare the selected files for context"""
        context = []
        for file_info in self.files:
            if file_info["path"] in self.selected:
                try:
                    with open(file_info["full_path"], "r", encoding="utf-8") as f:
                        content = []
                        for idx, line in enumerate(f, 1):
                            content.append(f"{idx:4} | {line.rstrip()}")
                        context.append({"path": file_info["path"], "content": "\n".join(content)})
                except UnicodeDecodeError:
                    context.append({"path": file_info["path"], "content": "[Binary file]"})
                except Exception as e:
                    context.append(
                        {"path": file_info["path"], "content": f"[Error reading file: {str(e)}]"}
                    )
        return context
