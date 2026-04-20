# MCP Cheat Sheet: Build Servers, Clients, and Tools with the Model Context Protocol

**TLDR;** A practical, code-first guide to building MCP servers, clients, and tools using the Python SDK. Covers the three core primitives (tools, resources, prompts), transport options, lifespan management, and a case study building a custom MCP server that wraps LangGraph's `PostgresStore` (backed by Supabase) -- because no LangGraph MCP server exists. LangGraph agents are always MCP *clients*; if you want store operations over MCP, you build the server yourself. Follows the structure of Anthropic's "Building with the Claude API" course.

---

## 1. What is MCP?

The Model Context Protocol is an open standard that defines how LLM applications talk to external data sources and tools. Think of it as a USB-C port for AI: one standardized interface that replaces a tangle of custom integrations.

MCP servers expose three primitives:

| Primitive | Analogy | Purpose |
|-----------|---------|---------|
| **Resources** | GET endpoints | Load data into the LLM's context |
| **Tools** | POST endpoints | Execute code, produce side effects |
| **Prompts** | Reusable templates | Pre-built interaction patterns |

The protocol uses JSON-RPC 2.0 over pluggable transports (stdio, Streamable HTTP, or the legacy SSE).

---

## 2. Project Setup

Install the SDK with `uv` (recommended) or `pip`:

```bash
# Create and activate a project
uv init my-mcp-project && cd my-mcp-project
uv venv && source .venv/bin/activate

# Install the MCP SDK with CLI extras
uv add "mcp[cli]"

# Or with pip
pip install "mcp[cli]"
```

For the LangGraph integration later, also install:

```bash
uv add langchain-mcp-adapters langgraph
```

---

## 3. Building an MCP Server

### 3.1 The Minimal Server

`FastMCP` is the high-level entry point. It auto-generates tool schemas from type hints and docstrings:

```python
# server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Demo Server")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

Run it:

```bash
uv run server.py
```

Test it with the MCP Inspector:

```bash
npx -y @modelcontextprotocol/inspector
# Then connect to http://localhost:8000/mcp in the Inspector UI
```

### 3.2 Transport Options

```python
# stdio (local processes, Claude Desktop)
mcp.run(transport="stdio")

# Streamable HTTP (preferred for network servers)
mcp.run(transport="streamable-http")

# SSE (legacy, avoid for new projects)
mcp.run(transport="sse")
```

---

## 4. Defining Tools

Tools are functions the LLM can call. They are expected to have side effects.

### 4.1 Basic Tool

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Tool Examples")


@mcp.tool()
def get_weather(city: str, unit: str = "celsius") -> str:
    """Get the current weather for a city."""
    return f"Weather in {city}: 22 degrees {unit[0].upper()}"
```

The decorator reads the function signature and docstring to build the JSON schema automatically. No manual schema definition required.

### 4.2 Async Tools

```python
import httpx


@mcp.tool()
async def fetch_url(url: str) -> str:
    """Fetch the content of a URL."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text[:2000]
```

### 4.3 Structured Output with Pydantic

```python
from pydantic import BaseModel, Field


class WeatherData(BaseModel):
    """Structured weather response."""

    temperature: float = Field(description="Temperature in Celsius")
    humidity: float = Field(description="Humidity percentage")
    condition: str


@mcp.tool()
def get_structured_weather(city: str) -> WeatherData:
    """Get structured weather data for a city."""
    return WeatherData(
        temperature=22.5,
        humidity=45.0,
        condition="sunny",
    )
```

The SDK validates the return value against the Pydantic model and generates an `outputSchema` for the client.

### 4.4 Error Handling

Three patterns, from simplest to most controlled:

```python
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import CallToolResult, TextContent


# Pattern 1: Raise ToolError (preferred)
@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide two numbers."""
    if b == 0:
        raise ToolError("Cannot divide by zero")
    return a / b


# Pattern 2: Unhandled exceptions are auto-caught
@mcp.tool()
def read_config(path: str) -> str:
    """Read a config file. FileNotFoundError becomes an error response."""
    with open(path) as f:
        return f.read()


# Pattern 3: Return CallToolResult for full control
@mcp.tool()
def validate_input(data: str) -> CallToolResult:
    """Validate input data with custom error content."""
    if len(data) < 3:
        return CallToolResult(
            content=[TextContent(type="text", text="Too short")],
            isError=True,
        )
    return CallToolResult(
        content=[TextContent(type="text", text="Valid")],
    )
```

### 4.5 Progress Reporting via Context

Inject a `Context` parameter to report progress, log messages, or access the session:

```python
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

mcp = FastMCP("Progress Demo")


@mcp.tool()
async def long_task(
    task_name: str,
    ctx: Context[ServerSession, None],
    steps: int = 5,
) -> str:
    """Run a task with progress updates."""
    for i in range(steps):
        await ctx.report_progress(
            progress=(i + 1) / steps,
            total=1.0,
            message=f"Step {i + 1}/{steps}",
        )
        await ctx.info(f"Completed step {i + 1}")
    return f"Task '{task_name}' done"
```

---

## 5. Defining Resources

Resources provide data to the LLM. They should not produce side effects.

### 5.1 Static and Templated Resources

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Resource Examples")


# Static resource (fixed URI)
@mcp.resource("config://settings")
def get_settings() -> str:
    """Return application settings."""
    return '{"theme": "dark", "language": "en"}'


# Templated resource (URI parameters extracted automatically)
@mcp.resource("users://{user_id}/profile")
def get_user_profile(user_id: str) -> str:
    """Fetch a user profile by ID."""
    return f'{{"user_id": "{user_id}", "name": "User {user_id}"}}'


# Multi-parameter template
@mcp.resource("repos://{owner}/{repo}/readme")
def get_readme(owner: str, repo: str) -> str:
    """Get a repo README."""
    return f"README content for {owner}/{repo}"
```

### 5.2 Binary Resources

```python
@mcp.resource("images://logo.png", mime_type="image/png")
def get_logo() -> bytes:
    """Return a binary image. Auto base64-encoded by the SDK."""
    with open("logo.png", "rb") as f:
        return f.read()
```

---

## 6. Defining Prompts

Prompts are reusable conversation templates:

```python
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

mcp = FastMCP("Prompt Examples")


# Simple string prompt
@mcp.prompt(title="Code Review")
def review_code(code: str) -> str:
    """Generate a code review prompt."""
    return f"Please review this code:\n\n{code}"


# Multi-turn prompt with message objects
@mcp.prompt(title="Debug Assistant")
def debug_error(error: str) -> list[base.Message]:
    """Create a debugging conversation."""
    return [
        base.UserMessage("I'm seeing this error:"),
        base.UserMessage(error),
        base.AssistantMessage(
            "I'll help debug that. What have you tried so far?"
        ),
    ]
```

---

## 7. Lifespan Management

Use the `lifespan` parameter to manage startup/shutdown of shared resources like database connections:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession


class Database:
    """Your actual database class."""

    @classmethod
    async def connect(cls, uri: str) -> "Database":
        # ... real connection logic
        return cls()

    async def disconnect(self) -> None:
        pass

    async def query(self, sql: str) -> list[dict]:
        return [{"result": "data"}]


@dataclass
class AppContext:
    """Typed container for lifespan-scoped dependencies."""

    db: Database


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Initialize on startup, clean up on shutdown."""
    db = await Database.connect("postgresql://localhost/mydb")
    try:
        yield AppContext(db=db)
    finally:
        await db.disconnect()


mcp = FastMCP("DB Server", lifespan=app_lifespan)


@mcp.tool()
async def run_query(
    sql: str,
    ctx: Context[ServerSession, AppContext],
) -> str:
    """Execute a SQL query using the lifespan-managed connection."""
    db = ctx.request_context.lifespan_context.db
    results = await db.query(sql)
    return str(results)
```

---

## 8. Writing an MCP Client

### 8.1 Stdio Client (Local Server)

```python
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["server.py"],
)


async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Discover capabilities
            tools = await session.list_tools()
            print([t.name for t in tools.tools])

            resources = await session.list_resources()
            print([r.uri for r in resources.resources])

            prompts = await session.list_prompts()
            print([p.name for p in prompts.prompts])

            # Call a tool
            result = await session.call_tool(
                "add", arguments={"a": 5, "b": 3}
            )
            print(result.content[0].text)  # "8"


asyncio.run(main())
```

### 8.2 Streamable HTTP Client (Remote Server)

```python
import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    async with streamable_http_client(
        "http://localhost:8000/mcp"
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"{tool.name}: {tool.description}")


asyncio.run(main())
```

### 8.3 Reading Resources from the Client

```python
from pydantic import AnyUrl

# Read a static resource
content = await session.read_resource(AnyUrl("config://settings"))
print(content.contents[0].text)

# Read a templated resource
content = await session.read_resource(AnyUrl("users://alice/profile"))
print(content.contents[0].text)
```

### 8.4 Using Prompts from the Client

```python
prompt_result = await session.get_prompt(
    "review_code",
    arguments={"code": "def foo(): pass"},
)
# prompt_result.messages contains the rendered conversation
for msg in prompt_result.messages:
    print(f"{msg.role}: {msg.content}")
```

---

## 9. Mounting on an Existing ASGI App

You can embed an MCP server inside a FastAPI or Starlette app:

```python
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

app = FastAPI()
mcp = FastMCP("Embedded Server")


@mcp.tool()
def greet(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"


# Mount at /mcp
app = mcp.streamable_http_app()

# Or mount alongside other routes:
# from starlette.routing import Mount
# app.routes.append(Mount("/mcp", app=mcp.streamable_http_app()))
```

---

## 10. Case Study: Building an MCP Server for LangGraph's PostgresStore

**Key insight:** No LangGraph MCP server exists. LangGraph is always on the *client* side of MCP, consuming tools that other servers expose. If you want agents to interact with LangGraph's `PostgresStore` via MCP, you have to build that server yourself.

This section shows how to wrap `PostgresStore` (backed by Supabase) in a custom MCP server, then connect agents to it.

### 10.1 Why Build This?

LangGraph's `PostgresStore` provides a key-value store with vector search, namespacing, and metadata indexing. Wrapping it in MCP means:

- Any MCP client (Claude Desktop, another LangGraph agent, a custom script) can `put`, `search`, and `get` items without importing LangGraph directly.
- The store's domain logic (namespaces, embedding, indexing) stays encapsulated on the server side.
- You get transport flexibility: stdio for local, Streamable HTTP for network.

### 10.2 The PostgresStore MCP Server

```python
# langgraph_store_server.py
"""MCP server wrapping LangGraph's PostgresStore.

Exposes put, get, search, and delete as MCP tools.
Any MCP client can interact with the store without
importing LangGraph.
"""
import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from langgraph.store.postgres import AsyncPostgresStore
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.session import ServerSession


@dataclass
class StoreContext:
    """Lifespan-scoped container for the async store."""

    store: AsyncPostgresStore


@asynccontextmanager
async def store_lifespan(
    server: FastMCP,
) -> AsyncIterator[StoreContext]:
    """Initialize PostgresStore on startup, close on shutdown."""
    db_uri = os.environ["STORE_DB_URI"]
    store = AsyncPostgresStore.from_conn_string(db_uri)
    await store.setup()
    try:
        yield StoreContext(store=store)
    finally:
        # AsyncPostgresStore manages its own pool; no explicit close needed
        pass


mcp = FastMCP("LangGraph Store", lifespan=store_lifespan)


def _get_store(
    ctx: Context[ServerSession, StoreContext],
) -> AsyncPostgresStore:
    """Extract the store from the lifespan context."""
    return ctx.request_context.lifespan_context.store


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def store_put(
    namespace: list[str],
    key: str,
    value: dict,
    index: list[str] | None = None,
    ctx: Context[ServerSession, StoreContext] = None,
) -> str:
    """Write an item to the store.

    Args:
        namespace: Hierarchical namespace, e.g. ["research", "signals"].
        key: Unique key within the namespace.
        value: JSON-serializable dict to store.
        index: Optional list of JSON field paths in `value` to index
               for vector search (e.g. ["embedding_text"]).
    """
    store = _get_store(ctx)
    await store.aput(
        namespace=tuple(namespace),
        key=key,
        value=value,
        index=index or False,
    )
    return f"Stored item {key} in {'/'.join(namespace)}"


@mcp.tool()
async def store_get(
    namespace: list[str],
    key: str,
    ctx: Context[ServerSession, StoreContext] = None,
) -> str:
    """Retrieve a single item by namespace and key.

    Returns the item's value as JSON, or an error if not found.
    """
    store = _get_store(ctx)
    item = await store.aget(namespace=tuple(namespace), key=key)
    if item is None:
        raise ToolError(
            f"No item found at {'/'.join(namespace)}/{key}"
        )
    return json.dumps(item.value, default=str)


@mcp.tool()
async def store_search(
    namespace_prefix: list[str],
    query: str | None = None,
    filter: dict | None = None,
    limit: int = 10,
    ctx: Context[ServerSession, StoreContext] = None,
) -> str:
    """Search the store by vector similarity and/or metadata filter.

    Args:
        namespace_prefix: Namespace prefix to search within.
        query: Natural language query for vector search.
               Omit to search by filter only.
        filter: Metadata filter dict, e.g. {"domain": "ai-science"}.
        limit: Max results to return.
    """
    store = _get_store(ctx)
    results = await store.asearch(
        namespace_prefix=tuple(namespace_prefix),
        query=query,
        filter=filter,
        limit=limit,
    )
    items = [
        {
            "namespace": list(r.namespace),
            "key": r.key,
            "value": r.value,
            "score": getattr(r, "score", None),
        }
        for r in results
    ]
    return json.dumps(items, default=str)


@mcp.tool()
async def store_delete(
    namespace: list[str],
    key: str,
    ctx: Context[ServerSession, StoreContext] = None,
) -> str:
    """Delete an item from the store by namespace and key."""
    store = _get_store(ctx)
    await store.adelete(namespace=tuple(namespace), key=key)
    return f"Deleted {key} from {'/'.join(namespace)}"


@mcp.tool()
async def store_list_namespaces(
    prefix: list[str] | None = None,
    max_depth: int | None = None,
    limit: int = 100,
    ctx: Context[ServerSession, StoreContext] = None,
) -> str:
    """List namespaces in the store, optionally filtered by prefix.

    Useful for discovering what data exists before searching.
    """
    store = _get_store(ctx)
    namespaces = await store.alist_namespaces(
        prefix=tuple(prefix) if prefix else None,
        max_depth=max_depth,
        limit=limit,
    )
    return json.dumps([list(ns) for ns in namespaces])


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("store://namespaces")
async def list_top_namespaces() -> str:
    """List top-level namespaces as a resource."""
    db_uri = os.environ["STORE_DB_URI"]
    store = AsyncPostgresStore.from_conn_string(db_uri)
    await store.setup()
    namespaces = await store.alist_namespaces(max_depth=2, limit=50)
    return json.dumps([list(ns) for ns in namespaces])


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt(title="Explore Store")
def explore_store(namespace: str = "research") -> str:
    """Prompt template for exploring what's in a namespace."""
    return (
        f"List all namespaces under ['{namespace}'], then search "
        f"for the 5 most recent items. Summarize what you find."
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

Run it:

```bash
export STORE_DB_URI="postgresql://postgres:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
python langgraph_store_server.py
```

Test with the Inspector:

```bash
npx -y @modelcontextprotocol/inspector
# Connect to http://localhost:8000/mcp
```

### 10.3 Connecting a LangGraph Agent as Client

Now any LangGraph agent can consume the store server via `langchain-mcp-adapters`. The agent discovers `store_put`, `store_get`, `store_search`, etc. as tools automatically:

```python
# agent.py
import asyncio

from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent


async def main():
    model = init_chat_model("anthropic:claude-sonnet-4-20250514")

    async with MultiServerMCPClient(
        {
            "store": {
                "url": "http://localhost:8000/mcp",
                "transport": "streamable_http",
            },
        }
    ) as client:
        tools = client.get_tools()
        agent = create_react_agent(model, tools)

        response = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "List all namespaces, then search the "
                            "'research' namespace for signals about "
                            "transformer architectures."
                        ),
                    }
                ]
            }
        )

        for msg in response["messages"]:
            print(f"\n{msg.type}: {msg.content}")


asyncio.run(main())
```

### 10.4 Stdio Transport (Local Subprocess)

For local use or Claude Desktop integration, run the server as a subprocess:

```python
async with MultiServerMCPClient(
    {
        "store": {
            "command": "python",
            "args": ["langgraph_store_server.py"],
            "transport": "stdio",
            "env": {
                "STORE_DB_URI": "postgresql://...",
            },
        },
    }
) as client:
    tools = client.get_tools()
    # ... same agent code
```

### 10.5 Multi-Server Composition

The real payoff: one agent consuming tools from the store server, a filesystem server, and a GitHub server simultaneously:

```python
async with MultiServerMCPClient(
    {
        "store": {
            "url": "http://localhost:8000/mcp",
            "transport": "streamable_http",
        },
        "filesystem": {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                "/path/to/allowed/dir",
            ],
            "transport": "stdio",
        },
        "github": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "transport": "stdio",
            "env": {"GITHUB_TOKEN": "ghp_xxx"},
        },
    }
) as client:
    # All tools from all servers, unified
    tools = client.get_tools()
    agent = create_react_agent(model, tools)
```

### 10.6 Architecture Summary

```
+---------------------+         +---------------------+
|  LangGraph Agent    |         |  Claude Desktop     |
|  (MCP Client)       |         |  (MCP Client)       |
+---------+-----------+         +---------+-----------+
          |                               |
          |  MCP (Streamable HTTP/stdio)   |
          |                               |
+---------v-------------------------------v-----------+
|           LangGraph Store MCP Server                |
|  (your code -- this does not exist as a package)    |
+---------+-------------------------------------------+
          |
          |  AsyncPostgresStore
          |
+---------v-----------+
|  Supabase / Postgres|
+---------------------+
```

The critical takeaway: **LangGraph provides no MCP server.** LangGraph agents are always MCP *clients*. If you want store operations exposed over MCP, you build the server yourself, wrapping `AsyncPostgresStore` (or your own repo layer) in FastMCP tools.

---

## 11. Testing

The SDK provides an in-memory transport for testing without network or subprocess overhead:

```python
# test_server.py
import pytest
from mcp.server.fastmcp import FastMCP


@pytest.fixture
def mcp_server():
    server = FastMCP("Test")

    @server.tool()
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    return server


@pytest.mark.anyio
async def test_add_tool(mcp_server):
    async with mcp_server.test_client() as client:
        result = await client.call_tool("add", {"a": 2, "b": 3})
        assert result.content[0].text == "5"


@pytest.mark.anyio
async def test_list_tools(mcp_server):
    async with mcp_server.test_client() as client:
        tools = await client.list_tools()
        names = [t.name for t in tools.tools]
        assert "add" in names
```

---

## 12. Claude Desktop Integration

To use your server with Claude Desktop, add it to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "supabase": {
      "command": "python",
      "args": ["/absolute/path/to/supabase_mcp_server.py"],
      "env": {
        "SUPABASE_DB_URI": "postgresql://..."
      }
    }
  }
}
```

Claude Desktop will spawn the server as a stdio subprocess and auto-discover its tools, resources, and prompts.

---

## 13. Quick Reference

### Server-Side Decorators

| Decorator | What It Registers | Return Type |
|-----------|------------------|-------------|
| `@mcp.tool()` | A callable tool | `str`, Pydantic model, `CallToolResult`, or any JSON-serializable type |
| `@mcp.resource("uri://...")` | A readable resource | `str` or `bytes` |
| `@mcp.prompt()` | A prompt template | `str` or `list[base.Message]` |

### Client-Side Methods

| Method | Purpose |
|--------|---------|
| `session.initialize()` | Handshake with the server |
| `session.list_tools()` | Discover available tools |
| `session.call_tool(name, args)` | Invoke a tool |
| `session.list_resources()` | Discover resources |
| `session.read_resource(uri)` | Read a resource |
| `session.list_prompts()` | Discover prompts |
| `session.get_prompt(name, args)` | Render a prompt |

### Transport Cheat Sheet

| Transport | Use When | Server Code | Client Code |
|-----------|----------|-------------|-------------|
| **stdio** | Local subprocess, Claude Desktop | `mcp.run(transport="stdio")` | `stdio_client(StdioServerParameters(...))` |
| **Streamable HTTP** | Network server, production | `mcp.run(transport="streamable-http")` | `streamable_http_client("http://host:8000/mcp")` |
| **SSE** | Legacy only | `mcp.run(transport="sse")` | `sse_client("http://host:8000/sse")` |

---

## Further Reading

- [MCP Python SDK Docs](https://py.sdk.modelcontextprotocol.io/)
- [MCP Specification](https://modelcontextprotocol.io)
- [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters)
- [Anthropic's "Building with the Claude API" Course](https://anthropic.skilljar.com/claude-with-the-anthropic-api)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)