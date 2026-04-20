import json
from typing import Literal

from anthropic.types import Message, ToolResultBlockParam
from mcp.types import CallToolResult, TextContent, Tool

from smartify.agentic_development.mcp_cli_project_COMPLETE.mcp_client import MCPClient


class ToolManager:
    """Manages MCP tool discovery and execution for Claude responses."""

    @classmethod
    async def get_all_tools(cls, clients: dict[str, MCPClient]) -> list[Tool]:
        """Collects tool definitions from all configured MCP clients.

        Args:
            clients: Mapping of client names to MCP client instances.

        Returns:
            A list of tool definitions formatted for the Claude API.
        """
        tools = []
        for client in clients.values():
            tool_models = await client.list_tools()
            tools += [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.inputSchema,
                }
                for t in tool_models
            ]
        return tools

    @classmethod
    async def _find_client_with_tool(
        cls, clients: list[MCPClient], tool_name: str
    ) -> MCPClient | None:
        """Finds the first client that exposes the requested tool.

        Args:
            clients: MCP clients to search.
            tool_name: Name of the tool to locate.

        Returns:
            The first matching client, or None if no client provides the tool.
        """
        for client in clients:
            tools = await client.list_tools()
            tool = next((t for t in tools if t.name == tool_name), None)
            if tool:
                return client
        return None

    @classmethod
    def _build_tool_result_part(
        cls,
        tool_use_id: str,
        text: str,
        status: Literal["success"] | Literal["error"],
    ) -> ToolResultBlockParam:
        """Builds a Claude-compatible tool result payload.

        Args:
            tool_use_id: Identifier of the originating tool request.
            text: Serialized tool output text.
            status: Execution status for the tool request.

        Returns:
            A tool result block ready to append to the message history.
        """
        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": text,
            "is_error": status == "error",
        }

    @classmethod
    async def execute_tool_requests(
        cls, clients: dict[str, MCPClient], message: Message
    ) -> list[ToolResultBlockParam]:
        """Executes tool requests found in a Claude message.

        Args:
            clients: Mapping of client names to MCP client instances.
            message: Claude response message that may contain tool use blocks.

        Returns:
            A list of tool result blocks corresponding to each tool request.
        """
        tool_requests = [
            block for block in message.content if block.type == "tool_use"
        ]
        tool_result_blocks: list[ToolResultBlockParam] = []
        for tool_request in tool_requests:
            tool_use_id = tool_request.id
            tool_name = tool_request.name
            tool_input = tool_request.input

            client = await cls._find_client_with_tool(
                list(clients.values()), tool_name
            )

            if not client:
                tool_result_part = cls._build_tool_result_part(
                    tool_use_id, "Could not find that tool", "error"
                )
                tool_result_blocks.append(tool_result_part)
                continue

            tool_output: CallToolResult | None = None
            try:
                tool_output = await client.call_tool(
                    tool_name, tool_input
                )
                items = []
                if tool_output:
                    items = tool_output.content
                content_list = [
                    item.text for item in items if isinstance(item, TextContent)
                ]
                content_json = json.dumps(content_list)
                tool_result_part = cls._build_tool_result_part(
                    tool_use_id,
                    content_json,
                    "error"
                    if tool_output and tool_output.isError
                    else "success",
                )
            except Exception as e:
                error_message = f"Error executing tool '{tool_name}': {e}"
                print(error_message)
                tool_result_part = cls._build_tool_result_part(
                    tool_use_id,
                    json.dumps({"error": error_message}),
                    "error"
                    if tool_output and tool_output.isError
                    else "success",
                )

            tool_result_blocks.append(tool_result_part)
        return tool_result_blocks
