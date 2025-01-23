"""Language model interaction module for diffdev.

This module provides a provider-agnostic interface for interacting with various
language models, managing prompt construction, response parsing, and error handling
for AI-assisted code modifications.
"""

import json
import logging
from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import anthropic
from colorama import Fore
from colorama import Style
from colorama import init
from openai import OpenAI

# Initialize colorama
init()

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    This class defines the interface that all LLM providers must implement,
    ensuring consistent interaction patterns across different services.
    """

    @abstractmethod
    def chat_completion(self, messages: List[Dict[str, str]], system: str = "", **kwargs) -> str:
        """Get chat completion from the provider.

        Args:
            messages: List of message dictionaries with role and content
            system: Optional system prompt
            **kwargs: Additional provider-specific arguments

        Returns:
            str: The model's response text

        Raises:
            Exception: If the API request fails
        """
        pass


class AnthropicProvider(LLMProvider):
    """Provider implementation for Anthropic's Claude API."""

    def __init__(self, api_key: str):
        """Initialize the Anthropic provider.

        Args:
            api_key: Anthropic API key for authentication
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"

    def chat_completion(self, messages: List[Dict[str, str]], system: str = "", **kwargs) -> str:
        """Get chat completion from Claude.

        Args:
            messages: List of message dictionaries
            system: Optional system prompt
            **kwargs: Additional arguments (ignored for Claude)

        Returns:
            str: Claude's response text

        Raises:
            anthropic.APIError: If the API request fails
        """
        try:
            logger.debug("Sending request to Anthropic API...")
            response = self.client.messages.create(
                max_tokens=8192,
                messages=messages,
                model=self.model,
                system=system,
                stream=True,
            )

            full_response = ""
            for chunk in response:
                if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                    chunk_text = chunk.delta.text
                    print(chunk_text, end="", flush=True)
                    full_response += chunk_text

            # Strip </answer> tag if end of response
            if full_response.endswith("</answer>"):
                full_response = full_response[:-9]

            return full_response.rstrip()

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


class DeepSeekProvider(LLMProvider):
    """Provider implementation for DeepSeek's API."""

    def __init__(self, api_key: str):
        """Initialize the DeepSeek provider.

        Args:
            api_key: DeepSeek API key for authentication
        """
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.model = "deepseek-reasoner"

    def chat_completion(self, messages: List[Dict[str, str]], system: str = "", **kwargs) -> str:
        """Get reasoning from DeepSeek.

        Args:
            messages: List of message dictionaries
            system: Optional system prompt (ignored for DeepSeek)
            **kwargs: Additional arguments (ignored for DeepSeek)

        Returns:
            str: The reasoning content from DeepSeek

        Raises:
            Exception: If the API request fails
        """
        try:
            logger.debug("Sending request to DeepSeek API...")
            response = self.client.chat.completions.create(
                model=self.model, messages=messages, stream=True
            )

            reasoning = "<thinking>\n"
            for chunk in response:
                if chunk.choices[0].delta.reasoning_content:
                    chunk_text = chunk.choices[0].delta.reasoning_content
                    print(chunk_text, end="", flush=True)  # Still print for user feedback
                    reasoning += chunk_text
            reasoning += "\n</thinking>\n<answer>"
            return reasoning.rstrip()

        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            raise


class LLMClient:
    """Provider-agnostic client for interacting with language models.

    This class manages communication with various LLM providers, handling
    prompt construction, response streaming, and error handling for
    AI-assisted code modifications.

    Attributes:
        providers (Dict[str, LLMProvider]): Map of provider names to instances
        chat_history (List[Dict[str, str]]): History of chat messages
    """

    def __init__(self):
        """Initialize the LLM client."""
        self.providers: Dict[str, LLMProvider] = {}
        self.chat_history: List[Dict[str, str]] = []

    def add_provider(self, name: str, provider: LLMProvider) -> None:
        """Add an LLM provider.

        Args:
            name: Unique identifier for the provider
            provider: Provider instance implementing LLMProvider
        """
        self.providers[name] = provider

    def get_provider(self, name: str) -> Optional[LLMProvider]:
        """Get a provider by name.

        Args:
            name: Provider identifier

        Returns:
            Optional[LLMProvider]: The provider if found, None otherwise
        """
        return self.providers.get(name)

    def chat(self, message: str, system_prompt: str = "") -> str:
        """Send a chat message and return the enhanced response.

        This method:
        1. Gets reasoning from DeepSeek if available
        2. Uses reasoning to enhance Claude's response
        3. Maintains chat history for context

        Args:
            message: User's message
            system_prompt: Optional system prompt

        Returns:
            str: The final response

        Raises:
            ValueError: If primary chat provider is not configured
            Exception: If API requests fail
        """
        try:
            # Add user message to history
            self.chat_history.append({"role": "user", "content": message})

            # Get reasoning if DeepSeek provider is available
            reasoning = ""
            if "deepseek" in self.providers:
                print(f"\n{Fore.CYAN}DeepSeek's Reasoning:{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'=' * 40}{Style.RESET_ALL}")
                reasoning = self.providers["deepseek"].chat_completion(
                    messages=[{"role": "user", "content": message}]
                )
                if not reasoning.strip():
                    print(f"\n{Fore.YELLOW}Note: No additional reasoning provided{Style.RESET_ALL}")
                print("\n")
                print(f"{Fore.CYAN}{'=' * 40}{Style.RESET_ALL}")

            # Prepare messages with optional reasoning
            messages = self.chat_history.copy()
            if reasoning.strip():
                messages.append({"role": "assistant", "content": reasoning})

            # Get completion from primary provider (Claude)
            if "anthropic" not in self.providers:
                raise ValueError("Primary chat provider (Anthropic) not configured")

            print(f"\n{Fore.GREEN}Claude's Response:{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'-' * 40}{Style.RESET_ALL}")
            response = self.providers["anthropic"].chat_completion(
                messages=messages, system=system_prompt
            )
            if not response.strip():
                print(
                    f"{Fore.RED}No response received from Claude. It's likely that Claude determined from the reasoning trace that there was no more left to say.{Style.RESET_ALL}"
                )
                return ""
            print(f"\n{Fore.GREEN}{'-' * 40}{Style.RESET_ALL}")

            # Add response to history
            self.chat_history.append({"role": "assistant", "content": response})
            return response

        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise

    def send_prompt(
        self, context: List[Dict[str, str]], prompt: str, system_prompt: str
    ) -> Dict[str, Any]:
        """Send a prompt to the LLM and return the parsed response.

        Sends the given prompt along with context to the primary provider (Claude)
        and streams the response, parsing it as JSON for code modifications.

        Args:
            context: List of message dicts with file content.
            prompt: User's prompt/request.
            system_prompt: System prompt for the provider.

        Returns:
            Dict[str, Any]: Parsed JSON response containing code modifications.

        Raises:
            ValueError: If primary provider not configured or response is not valid JSON.
            Exception: If API request fails.
        """
        try:
            # Verify primary provider is configured
            if "anthropic" not in self.providers:
                raise ValueError("Primary chat provider (Anthropic) not configured")

            # Prepare messages including context
            messages = context.copy()
            messages.append({"role": "user", "content": prompt})

            # Get completion from primary provider
            full_response = self.providers["anthropic"].chat_completion(
                messages=messages, system=system_prompt
            )

            json_str = self._extract_json(full_response)
            return json.loads(json_str)

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
