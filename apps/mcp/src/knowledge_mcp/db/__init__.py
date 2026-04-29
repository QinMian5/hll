"""
Abstract: Shared persistence helpers for the public Knowledge MCP service.
Out of scope: Runtime database session construction and migration execution.
"""

from knowledge_mcp.db.metadata import Base, metadata

__all__ = ["Base", "metadata"]
