"""
Abstract: Worker process import shell that bootstraps runtime and registers actors for Dramatiq.
Out of scope: Actor business logic and queue payload semantics.
"""

from __future__ import annotations

from entrypoints.worker.bootstrap import bootstrap_worker

bootstrap_worker()
