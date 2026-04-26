"""
Abstract: Taxonomy-classification aliases for shared job-queue HTTP helpers.
Out of scope: Local taxonomy assignment and webhook event persistence.
"""

from __future__ import annotations

from job_queue_integration.client import (
    AcceptedJobResult as AcceptedTaxonomyClassificationJobResult,
)
from job_queue_integration.client import (
    JobQueueClient as TaxonomyClassificationJobQueueClient,
)
from job_queue_integration.client import (
    JobResult as TaxonomyClassificationJobResult,
)
from job_queue_integration.client import (
    NotReadyJobResult as NotReadyTaxonomyClassificationJobResult,
)

__all__ = [
    "AcceptedTaxonomyClassificationJobResult",
    "NotReadyTaxonomyClassificationJobResult",
    "TaxonomyClassificationJobQueueClient",
    "TaxonomyClassificationJobResult",
]
