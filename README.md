# diffdev

diffdev is a command-line tool that helps you make repo-wide code changes using an AI assistant. It allows you to interactively select files, provide a prompt describing the desired changes, and apply the AI-generated modifications as a git patch.

## Key Features

- **File Selection**: Use a TUI to select files to include in the context
- **Context-Aware Changes**: The AI assistant analyzes the selected files and your prompt to generate contextual changes
- **Structured Patch Generation**: Changes are returned as a git-style patch for easy application and review
- **Revision Control Integration**: Apply patches using `git apply` and rollback changes when needed
- **Claude AI Assistant**: Leverages the powerful Claude language model from Anthropic

## Requirements

- Python 3.11 or higher
- Git installed and available in PATH
- Anthropic API key

## Installation

```bash
# Install from PyPI
pip install diffdev

# Set your Anthropic API key
export ANTHROPIC_API_KEY="your-api-key-here"
```

## Usage

1. Navigate to your git repository
2. Run `diffdev`
3. Use the TUI to select files for context:
   - Space: Toggle file/directory selection
   - Tab: Expand/collapse directories
   - Enter: Confirm selection
   - q: Quit selection
4. Enter your prompt describing the desired changes
5. Review and confirm the generated patch

### Commands

- `select`: Open file selector to update context
- `undo`: Rollback last applied changes
- `redo`: Reapply last rolled back changes
- `exit`: Exit diffdev

## Example

```bash
$ cd my-project
$ diffdev

Starting diffdev...
Select files to include in the context:
[ ] + src/
[ ] + tests/
[ ] README.md

# After selecting files and confirming...

Enter command or prompt: Add type hints to the User class methods

# AI will analyze files and generate changes
# Changes are applied as a git patch that can be rolled back if needed
```

## Development

Contributions are welcome! Please feel free to submit a Pull Request.
