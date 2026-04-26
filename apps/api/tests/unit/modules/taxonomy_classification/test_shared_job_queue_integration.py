"""
Abstract: Boundary tests for taxonomy-classification reuse of shared job-queue helpers.
Out of scope: HTTP transport behavior and JWT validation branches.
"""

from __future__ import annotations

from job_queue_integration.client import JobQueueClient
from job_queue_integration.token import ClientCredentialsTokenProvider
from job_queue_integration.webhook_auth import WebhookAuthVerifier

from modules.taxonomy_classification.auth import WebhookAuthVerifier as TaxonomyWebhookAuthVerifier
from modules.taxonomy_classification.job_queue_client import (
    TaxonomyClassificationJobQueueClient,
)
from modules.taxonomy_classification.job_queue_token import (
    ClientCredentialsTokenProvider as TaxonomyTokenProvider,
)


def test_taxonomy_classification_reuses_shared_job_queue_helpers() -> None:
    assert TaxonomyClassificationJobQueueClient is JobQueueClient
    assert TaxonomyTokenProvider is ClientCredentialsTokenProvider
    assert TaxonomyWebhookAuthVerifier is WebhookAuthVerifier
