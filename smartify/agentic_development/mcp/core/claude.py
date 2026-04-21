#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Smartify                                                                            #
# Description: Deep Learning and Generative AI Smartify Lab                                        #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /smartify/agentic_development/mcp/core                                              #
# Filename   : claude.py                                                                           #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/john-james-ai/smartify                                           #
# ------------------------------------------------------------------------------------------------ #
# Created    : Sunday April 19th 2026 10:32:14 pm                                                  #
# Modified   : Monday April 20th 2026 04:22:41 pm                                                  #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
from anthropic import Anthropic
from anthropic.types import Message


class Claude:
    """Wrapper for Anthropic Claude message interactions.

    Args:
        model: The Claude model identifier to use for requests.

    Attributes:
        client: Configured Anthropic API client.
        model: Claude model identifier used for chat requests.
    """

    def __init__(self, model: str):
        self.client = Anthropic()
        self.model = model

    def add_user_message(self, messages: list, message):
        """Append a user message payload to the message list.

        Args:
            messages: Conversation message list to update in place.
            message: Message content as a string or Anthropic message object.
        """
        user_message = {
            "role": "user",
            "content": message.content
            if isinstance(message, Message)
            else message,
        }
        messages.append(user_message)

    def add_assistant_message(self, messages: list, message):
        """Append an assistant message payload to the message list.

        Args:
            messages: Conversation message list to update in place.
            message: Message content as a string or Anthropic message object.
        """
        assistant_message = {
            "role": "assistant",
            "content": message.content
            if isinstance(message, Message)
            else message,
        }
        messages.append(assistant_message)

    def text_from_message(self, message: Message):
        """Extract plain-text blocks from an Anthropic message.

        Args:
            message: Anthropic message containing content blocks.

        Returns:
            A newline-joined string containing all text block content.
        """
        return "\n".join(
            [block.text for block in message.content if block.type == "text"]
        )

    def chat(
        self,
        messages,
        system=None,
        temperature=1.0,
        stop_sequences=None,
        tools=None,
        thinking=False,
        thinking_budget=1024,
    ) -> Message:
        """Send a chat request to Claude and return the response message.

        Args:
            messages: Conversation history in Anthropic message format.
            system: Optional system instruction string.
            temperature: Sampling temperature for response generation.
            stop_sequences: Optional sequence list that stops generation.
            tools: Optional tool definitions for tool-use capable models.
            thinking: Whether to enable extended thinking mode.
            thinking_budget: Token budget for thinking mode when enabled.

        Returns:
            The created Anthropic message response.
        """
        stop_sequences = stop_sequences or []
        params = {
            "model": self.model,
            "max_tokens": 8000,
            "messages": messages,
            "temperature": temperature,
            "stop_sequences": stop_sequences,
        }

        if thinking:
            params["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget,
            }

        if tools:
            params["tools"] = tools

        if system:
            params["system"] = system

        message = self.client.messages.create(**params)
        return message
