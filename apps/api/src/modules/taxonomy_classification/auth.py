"""
Abstract: Taxonomy-classification aliases for shared job-queue webhook auth.
Out of scope: HTTP route handling and webhook event persistence behavior.
"""

from __future__ import annotations

from job_queue_integration.webhook_auth import (
    WebhookAuthenticationError,
    WebhookAuthInfrastructureError,
    WebhookAuthVerifier,
    WebhookPrincipal,
    WebhookReceiverAuthSettings,
)

__all__ = [
    "WebhookAuthInfrastructureError",
    "WebhookAuthVerifier",
    "WebhookAuthenticationError",
    "WebhookPrincipal",
    "WebhookReceiverAuthSettings",
]
