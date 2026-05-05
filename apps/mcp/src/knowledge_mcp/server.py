"""
Abstract: Runtime composition for the public Knowledge MCP protocol server.
Out of scope: HTTP routing, deployment process management, and operator configuration.
"""

from __future__ import annotations

from typing import Annotated
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field

from knowledge_mcp.auth.context import current_mcp_session_id, current_request_id
from knowledge_mcp.search_tool import SearchTool

_LOCAL_ALLOWED_HOSTS = ("127.0.0.1:*", "localhost:*", "[::1]:*")
_LOCAL_ALLOWED_ORIGINS = (
    "http://127.0.0.1:*",
    "http://localhost:*",
    "http://[::1]:*",
    "https://127.0.0.1:*",
    "https://localhost:*",
    "https://[::1]:*",
)


def create_mcp_server(
    *,
    search_tool: SearchTool | None = None,
    public_base_url: str | None = None,
) -> FastMCP:
    server = FastMCP(
        "Knowledge Search",
        json_response=True,
        stateless_http=False,
        streamable_http_path="/",
        transport_security=_transport_security(public_base_url),
    )

    if search_tool is not None:

        @server.tool()
        async def search(query: Annotated[str, Field(min_length=1)]) -> dict[str, object]:
            """Search the knowledge system for matching cards and connected titles."""
            return await search_tool.search(
                query,
                request_id=current_request_id(),
                mcp_session_id=current_mcp_session_id(),
            )

    return server


def _transport_security(public_base_url: str | None) -> TransportSecuritySettings | None:
    if public_base_url is None:
        return None

    parsed_url = urlparse(public_base_url)
    if not parsed_url.scheme or not parsed_url.netloc:
        return None

    public_origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
    return TransportSecuritySettings(
        allowed_hosts=_deduplicate((*_LOCAL_ALLOWED_HOSTS, parsed_url.netloc)),
        allowed_origins=_deduplicate((*_LOCAL_ALLOWED_ORIGINS, public_origin)),
    )


def _deduplicate(values: tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
