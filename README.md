# diffdev

diffdev is a command-line tool that helps you make repo-wide code changes using an AI assistant. It allows you to interactively select files, provide a prompt describing the desired changes, and apply the AI-generated modifications as a git patch.

## Key Features

- **File Selection**: Use a TUI to select files to include in the context
- **Context-Aware Changes**: The AI assistant analyzes the selected files and your prompt to generate contextual changes
- **Structured Patch Generation**: Changes are returned as a git-style patch for easy application and review
- **Revision Control Integration**: Apply patches using `git apply` and rollback changes when needed
- **Claude AI Assistant**: Leverages the powerful Claude language model from Anthropic
