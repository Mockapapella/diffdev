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

        API keys are loaded from environment variables during initialization.
        """
        self._anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self._deepseek_key = os.getenv("DEEPSEEK_API_KEY")

    def get_anthropic_key(self) -> Optional[str]:
        """Retrieve the Anthropic API key.

        Returns:
            Optional[str]: The API key if set, None otherwise.
        """
        return self._anthropic_key

    def get_deepseek_key(self) -> Optional[str]:
        """Retrieve the DeepSeek API key.

        Returns:
            Optional[str]: The API key if set, None otherwise.
        """
        return self._deepseek_key

    def validate_frankenclaude_keys(self) -> tuple[bool, str]:
        """Validate both API keys are present for FrankenClaude mode.

        Returns:
            tuple[bool, str]: A tuple containing:
                - bool: True if both keys are present, False otherwise
                - str: Error message if validation fails, empty string if successful
        """
        if not self._anthropic_key:
            return False, "ANTHROPIC_API_KEY environment variable not set"
        if not self._deepseek_key:
            return False, "DEEPSEEK_API_KEY environment variable not set"
        return True, ""

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
