# diffdev

diffdev is a command-line tool that helps you make repo-wide code changes using an AI assistant. It allows you to interactively select files, provide a prompt describing the desired changes, and apply the AI-generated modifications as a git patch.

This is half my experimental playground, half useful tool for the community. Pull requests for wacky experiments welcome.

## Key Features

- **File Selection**: Use a TUI to select files to include in the context
- **Context-Aware Changes**: The AI assistant analyzes the selected files and your prompt to generate contextual changes
- **Structured Patch Generation**: Changes are returned as a git-style patch for easy application and review
- **Revision Control Integration**: Apply patches using `git apply` and rollback changes when needed
- **Claude AI Assistant**: Leverages the powerful Claude language model from Anthropic
- **FrankenClaude Mode**: Enhanced capabilities by combining multiple AI models
- **Colored Output**: Improved readability with color-coded responses

## Installation

If you have `uv` installed, you can just run

```bash
uvx diffdev
```

Make sure you have your Anthropic API key set if you want to use the main tool. If you want to use the FrankenClaude flag you also need to have a DeepSeek key set.

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
export DEEPSEEK_API_KEY="your-api-key-here"
```

## Usage

1. Navigate to your git repository
1. Run `diffdev`
1. Use the TUI to select files for context:
   - Space: Toggle file/directory selection
   - Tab: Expand/collapse directories
   - Enter: Confirm selection
   - q: Quit selection
1. Enter your prompt describing the desired changes
1. Review and confirm the generated patch

Run `uvx diffdev --help` for additional flags.

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

## TODO

- Fix bug in TUI file selector where directories with selected files don't show filled selector
- Add agents functionality (multiple LLMs solving same problem with result aggregation)
- Support OpenAI API compatible endpoints (with port configuration)
- Allow specifying model name to use
- Add general model configuration file
- Add flag to specify API key
- Add retry/refix functionality for failed diffs
- Add retry/fix for invalid JSON LLM responses
- Enhance TUI with more color options
- Improve code modularization
- Add automatic file searching capability
- Add tool support for fetching up-to-date documentation
- Add navigation system for reviewing changes in current session
- Add reference system for previous changes in current session
