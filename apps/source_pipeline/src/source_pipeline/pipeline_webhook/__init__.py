"""
Abstract: Source-pipeline webhook intake package.
Out of scope: Runtime orchestration and queue result retrieval.
"""

from source_pipeline.pipeline_webhook.contracts import JobQueueWebhookPayload
from source_pipeline.pipeline_webhook.repository import JobQueueWebhookEventRepository

__all__ = ["JobQueueWebhookEventRepository", "JobQueueWebhookPayload"]
