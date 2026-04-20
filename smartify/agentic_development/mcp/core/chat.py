from anthropic.types import MessageParam

from smartify.agentic_development.mcp.core.claude import Claude
from smartify.agentic_development.mcp.core.tools import ToolManager
from smartify.agentic_development.mcp.mcp_client import MCPClient


class Chat:
    """Coordinates chat execution between Claude and MCP-backed tools.

    Args:
        claude_service: Service used to send messages to Claude and parse
            responses.
        clients: Mapping of MCP client names to initialized client instances.

    Attributes:
        claude_service: Service used to send messages to Claude and parse
            responses.
        clients: MCP clients available for tool discovery and execution.
        messages: Conversation history exchanged with the model.
    """

    def __init__(self, claude_service: Claude, clients: dict[str, MCPClient]):
        self.claude_service: Claude = claude_service
        self.clients: dict[str, MCPClient] = clients
        self.messages: list[MessageParam] = []

    async def _process_query(self, query: str):
        self.messages.append({"role": "user", "content": query})

    async def run(
        self,
        query: str,
    ) -> str:
        """Runs the chat loop until Claude returns a final text response.

        Args:
            query: Initial user query to send to the assistant.

        Returns:
            The final text response produced after any required tool calls.
        """
        final_text_response = ""

        await self._process_query(query)

        while True:
            response = self.claude_service.chat(
                messages=self.messages,
                tools=await ToolManager.get_all_tools(self.clients),
            )

            self.claude_service.add_assistant_message(self.messages, response)

            if response.stop_reason == "tool_use":
                print(self.claude_service.text_from_message(response))
                tool_result_parts = await ToolManager.execute_tool_requests(
                    self.clients, response
                )

                self.claude_service.add_user_message(
                    self.messages, tool_result_parts
                )
            else:
                final_text_response = self.claude_service.text_from_message(
                    response
                )
                break

        return final_text_response
