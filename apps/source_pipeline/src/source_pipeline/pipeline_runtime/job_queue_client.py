"""
Abstract: Source-pipeline aliases for shared job-queue HTTP helpers.
Out of scope: Orchestrator state transitions and operator-history reads.
"""

from __future__ import annotations

from job_queue_integration.client import (
    AcceptedJobResult,
    JobQueueClient,
    JobResult,
    NotReadyJobResult,
)

__all__ = ["AcceptedJobResult", "JobQueueClient", "JobResult", "NotReadyJobResult"]
