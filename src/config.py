import os
from typing import Optional


class ConfigManager:
    def __init__(self):
        self._api_key = os.getenv("ANTHROPIC_API_KEY")

    def get_api_key(self) -> Optional[str]:
        return self._api_key

    def get_system_prompt(self) -> str:
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
