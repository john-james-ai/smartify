#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Smartify                                                                            #
# Description: Deep Learning and Generative AI Smartify Lab                                        #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /smartify/agentic_development/mcp_cli_project_COMPLETE                              #
# Filename   : main.py                                                                             #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/john-james-ai/smartify                                           #
# ------------------------------------------------------------------------------------------------ #
# Created    : Sunday April 19th 2026 10:32:39 pm                                                  #
# Modified   : Monday April 20th 2026 12:16:24 am                                                  #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Runs the MCP CLI application backed by Claude and MCP clients.

This module loads environment configuration, initializes the primary
documentation server and any additional MCP servers provided on the command
line, and starts the interactive CLI chat session.
"""

import asyncio
import os
import sys
from contextlib import AsyncExitStack

from dotenv import load_dotenv

from smartify.agentic_development.mcp_cli_project_COMPLETE.core.claude import Claude
from smartify.agentic_development.mcp_cli_project_COMPLETE.core.cli import CliApp
from smartify.agentic_development.mcp_cli_project_COMPLETE.core.cli_chat import CliChat
from smartify.agentic_development.mcp_cli_project_COMPLETE.mcp_client import MCPClient

load_dotenv()

# Anthropic Config
claude_model = os.getenv("CLAUDE_MODEL", "")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")


assert claude_model, "Error: CLAUDE_MODEL cannot be empty. Update .env"
assert anthropic_api_key, (
    "Error: ANTHROPIC_API_KEY cannot be empty. Update .env"
)


async def main():
    """Initializes clients and starts the interactive CLI application.

    The function creates a Claude service, connects to the default
    documentation MCP server, optionally connects to additional servers passed
    on the command line, and runs the CLI lifecycle.
    """
    claude_service = Claude(model=claude_model)

    server_scripts = sys.argv[1:]
    clients = {}

    command, args = (
        ("uv", ["run", "mcp_server.py"])
        if os.getenv("USE_UV", "0") == "1"
        else ("python", ["mcp_server.py"])
    )

    async with AsyncExitStack() as stack:
        doc_client = await stack.enter_async_context(
            MCPClient(command=command, args=args)
        )
        clients["doc_client"] = doc_client

        for i, server_script in enumerate(server_scripts):
            client_id = f"client_{i}_{server_script}"
            client = await stack.enter_async_context(
                MCPClient(command="uv", args=["run", server_script])
            )
            clients[client_id] = client

        chat = CliChat(
            doc_client=doc_client,
            clients=clients,
            claude_service=claude_service,
        )

        cli = CliApp(chat)
        await cli.initialize()
        await cli.run()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
