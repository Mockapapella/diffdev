"""Language model interaction module for diffdev.

This module handles communication with Anthropic's Claude API, managing
prompt construction, response parsing, and error handling for AI-assisted
code modifications.
"""

import json
import logging
from typing import Any
from typing import Dict
from typing import List

import anthropic

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with Anthropic's Claude API.

    This class manages all communication with the Claude language model,
    handling prompt construction, response streaming, and JSON parsing.
    It ensures reliable communication and proper error handling for
    AI-assisted code modifications.

    Attributes:
        client (anthropic.Anthropic): Anthropic API client instance.
        model (str): The specific Claude model version to use.
    """

    def __init__(self, api_key: str):
        """Initialize the LLM client.

        Args:
            api_key (str): Anthropic API key for authentication.
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        # Use the model you need; just leaving as is
        self.model = "claude-3-5-sonnet-20241022"

    def send_prompt(
        self, context: List[Dict[str, str]], prompt: str, system_prompt: str
    ) -> Dict[str, Any]:
        """Send a prompt to the LLM and return the parsed response.

        Sends the given prompt along with context to Claude and streams the response,
        parsing it as JSON for code modifications.

        Args:
            context: List of message dicts with file content.
            prompt: User's prompt/request.
            system_prompt: System prompt for Claude.

        Returns:
            Dict[str, Any]: Parsed JSON response containing code modifications.

        Raises:
            ValueError: If response is not valid JSON.
            anthropic.APIError: If API request fails.
        """
        try:
            # Prepare messages including context
            messages = context.copy()
            messages.append({"role": "user", "content": prompt})

            # Stream response from API
            response = self.client.messages.create(
                max_tokens=8192,
                messages=messages,
                model=self.model,
                system=system_prompt,
                stream=True,
            )

            # Collect response chunks
            full_response = ""
            for chunk in response:
                if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                    chunk_text = chunk.delta.text
                    print(chunk_text, end="", flush=True)
                    full_response += chunk_text

            json_str = self._extract_json(full_response)
            return json.loads(json_str)

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise

        except json.JSONDecodeError as e:
            # If parsing failed, log and raise
            logger.error(f"Failed to parse JSON from LLM response:\n{full_response}")
            raise ValueError(
                f"Failed to parse JSON from LLM response: {str(e)}. "
                "Check that the system prompt requests JSON output."
            )

        except Exception as e:
            logger.error(f"Error in LLM communication: {e}")
            raise

    def _extract_json(self, text: str) -> str:
        """Extract valid JSON from the LLM response text.

        Attempts multiple strategies to find and extract valid JSON from the response:
        1. Look for a ```json fenced code block
        2. Try the entire response as JSON
        3. Attempt to locate a JSON object using braces

        Args:
            text (str): Raw response text from the LLM.

        Returns:
            str: Extracted JSON string.

        Raises:
            ValueError: If no valid JSON could be extracted.
        """
        json_start_token = "```json"
        json_end_token = "```"

        # 1. Attempt to find a fenced code block
        if json_start_token in text:
            start = text.find(json_start_token) + len(json_start_token)
            end = text.find(json_end_token, start)
            if end == -1:
                raise ValueError("Found ```json but no closing ``` fence in LLM response.")
            extracted = text[start:end].strip()
            try:
                # Test if it's valid JSON
                json.loads(extracted)
                return extracted
            except json.JSONDecodeError:
                logger.debug("Fenced JSON block found but not valid JSON. Trying fallback methods.")

        # 2. Try to parse entire response
        stripped = text.strip()
        try:
            json.loads(stripped)
            return stripped
        except json.JSONDecodeError:
            logger.debug("Entire response not valid JSON. Trying to find a subset.")

        # 3. Locate a JSON object by first '{' and last '}'
        first_brace = stripped.find("{")
        last_brace = stripped.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            subset = stripped[first_brace : last_brace + 1].strip()
            try:
                json.loads(subset)
                return subset
            except json.JSONDecodeError:
                logger.debug("Found braces but subset is not valid JSON.")

        # If all fails
        raise ValueError("No valid JSON could be extracted from the LLM response.")
