"""Configuration management module for diffdev.

This module provides configuration management functionality, including API key handling
and system prompt configuration for the diffdev tool.
"""

import os
from typing import Optional


class ConfigManager:
    """Manages configuration settings for the diffdev tool.

    This class handles various configuration aspects including API key management
    and system prompt settings. It provides a centralized way to access and manage
    configuration across the application.

    Attributes:
        _api_key (Optional[str]): The Anthropic API key loaded from environment variables.
    """

    def __init__(self):
        """Initialize the configuration manager.

        The API key is loaded from the ANTHROPIC_API_KEY environment variable during
        initialization.
        """
        self._api_key = os.getenv("ANTHROPIC_API_KEY")

    def get_api_key(self) -> Optional[str]:
        """Retrieve the Anthropic API key.

        Returns:
            Optional[str]: The API key if set, None otherwise.
        """
        return self._api_key

    def get_system_prompt(self) -> str:
        """Get the system prompt for the AI model.

        Returns:
            str: The system prompt that instructs the AI how to format its responses
                for code changes.
        """
        return """You are a helpful AI coding assistant. When asked to make changes to code files:
1. Analyze the provided files and context
2. Return your response as JSON with this structure:
{
    "files": [
        {
            "filename": "path/to/file",
            "changes": [
                {
                    "search": ["exact lines", "to find"],
                    "replace": ["new lines", "to insert"]
                }
            ]
        }
    ]
}"""
