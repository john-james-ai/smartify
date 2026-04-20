#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Smartify                                                                            #
# Version    : <<version>>                                                                         #
# Python     : 3.14.3                                                                              #
# Filepath   : /                                                                                   #
# Filename   : mcp_client.py                                                                       #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/john-james-ai/smartify                                           #
# ------------------------------------------------------------------------------------------------ #
# Created    : Sunday April 19th 2026 10:32:16 pm                                                  #
# Modified   : Monday April 20th 2026 09:48:47 am                                                  #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
import asyncio
import json
import sys
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from pydantic import AnyUrl


class MCPClient:
    """Model Context Protocol (MCP) client for communicating with MCP servers.

    This class manages connection and communication with MCP servers via stdio transport.
    It handles server initialization, tool listing and execution, and resource access.

    Args:
        command: The command to execute the MCP server (e.g., 'uv', 'python').
        args: Arguments to pass to the command.
        env: Optional environment variables for the server process.

    Attributes:
        _command: The command to execute the server.
        _args: Arguments for the server command.
        _env: Environment variables for the server process.
        _session: The ClientSession instance for MCP communication.
        _exit_stack: AsyncExitStack for managing async context resources.
    """
    def __init__(
        self,
        command: str,
        args: list[str],
        env: dict | None = None,
    ) -> None:
        """Initialize the MCP client.

        Args:
            command: The command to execute the MCP server.
            args: Arguments to pass to the server command.
            env: Optional environment variables for the server process. Defaults to None.
        """
        self._command = command
        self._args = args
        self._env = env
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack = AsyncExitStack()

    async def connect(self) -> None:
        """Connect to the MCP server and initialize the session.

        This method establishes a stdio transport connection to the server and
        initializes the client session.

        Raises:
            ConnectionError: If the server fails to initialize.
        """
        server_params = StdioServerParameters(
            command=self._command,
            args=self._args,
            env=self._env,
        )
        stdio_transport = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        _stdio, _write = stdio_transport
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(_stdio, _write)
        )
        await self._session.initialize()

    def session(self) -> ClientSession:
        """Get the active client session.

        Returns:
            The ClientSession instance for communicating with the MCP server.

        Raises:
            ConnectionError: If the session has not been initialized. Call connect() first.
        """
        if self._session is None:
            raise ConnectionError(
                "Client session not initialized or cache not populated. Call connect_to_server first."
            )
        return self._session

    async def list_tools(self) -> list[types.Tool]:
        """List all tools available from the MCP server.

        Returns:
            A list of Tool objects provided by the server.
        """
        result = await self.session().list_tools()
        return result.tools

    async def call_tool(
        self, tool_name: str, tool_input: dict
    ) -> types.CallToolResult | None:
        """Call a tool on the MCP server.

        Args:
            tool_name: The name of the tool to call.
            tool_input: Dictionary of input parameters for the tool.

        Returns:
            The result of the tool call, or None if no result is returned.
        """
        return await self.session().call_tool(tool_name, tool_input)

    async def list_prompts(self) -> list[types.Prompt]:
        """List all prompts available from the MCP server.

        Returns:
            A list of Prompt objects provided by the server.

        Note:
            TODO: Return a list of prompts defined by the MCP server
        """
        result = await self.session().list_prompts()
        return result.prompts

    async def get_prompt(self, prompt_name: str, args: dict[str, str]) -> list:
        """Get a specific prompt from the MCP server.

        Args:
            prompt_name: The name of the prompt to retrieve.
            args: Dictionary of arguments for the prompt.

        Returns:
            The prompt data or an empty list if not found.

        Note:
            TODO: Get a particular prompt defined by the MCP server
        """
        result = await self.session().get_prompt(prompt_name, args)
        return result.messages

    async def read_resource(self, uri: str) -> Any:
        """Read a resource from the MCP server.

        Args:
            uri: The URI of the resource to read.

        Returns:
            The resource content. If the resource is JSON, returns parsed data;
            otherwise returns the text content.
        """
        result = await self.session().read_resource(AnyUrl(uri))
        resource = result.contents[0]
        if isinstance(resource, types.TextResourceContents):
            if resource.mimeType == "application/json":
                return json.loads(resource.text)
            return resource.text

    async def cleanup(self) -> None:
        """Clean up resources and close the connection.

        This method closes the exit stack and clears the session reference.
        """
        await self._exit_stack.aclose()
        self._session = None

    async def __aenter__(self) -> MCPClient:
        """Enter the async context manager.

        Returns:
            The MCPClient instance after connecting to the server.
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async context manager and clean up resources.

        Args:
            exc_type: The exception type if an exception occurred.
            exc_val: The exception value if an exception occurred.
            exc_tb: The exception traceback if an exception occurred.
        """
        await self.cleanup()


# For testing
async def main() -> None:
    """Test the MCPClient by connecting to a server and listing available tools.

    This is a simple test function that demonstrates how to use the MCPClient
    as an async context manager.
    """
    async with MCPClient(
        # If using Python without UV, update command to 'python' and remove "run" from args.
        command="uv",
        args=["run", "mcp_server.py"],
    ) as _client:
        result = await _client.list_tools()
        print(result)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
