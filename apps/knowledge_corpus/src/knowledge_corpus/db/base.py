"""
Abstract: Declarative base module for app-local SQLAlchemy metadata.
Out of scope: Engine construction and session-factory lifecycle behavior.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
