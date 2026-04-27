"""
Abstract: Runtime composition for the public Knowledge MCP protocol server.
Out of scope: HTTP routing, deployment process management, and operator configuration.
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from knowledge_mcp.auth.context import current_request_id
from knowledge_mcp.search_tool import SearchTool


def create_mcp_server(*, search_tool: SearchTool | None = None) -> FastMCP:
    server = FastMCP(
        "Knowledge Search",
        json_response=True,
        stateless_http=True,
        streamable_http_path="/",
    )

    if search_tool is not None:

        @server.tool()
        async def search(query: Annotated[str, Field(min_length=1)]) -> dict[str, object]:
            """Search the knowledge system for matching cards and connected titles."""
            return await search_tool.search(query, request_id=current_request_id())

    return server
