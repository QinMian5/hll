"""
Abstract: Shared SQLAlchemy declarative base and metadata for MCP-owned persistence tables.
Out of scope: Table definitions and Alembic environment wiring.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

metadata = MetaData()


class Base(DeclarativeBase):
    metadata = metadata


__all__ = ["Base", "metadata"]
