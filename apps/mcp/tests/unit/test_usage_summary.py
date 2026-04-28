"""
Abstract: Unit tests for MCP dashboard usage-summary request and response models.
Out of scope: HTTP routing, service-token verification, and database connectivity.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from knowledge_mcp.usage.summary import (
    UsageSummaryRequest,
    UsageSummaryRow,
    dedupe_pat_fingerprints,
)

PAT_A = "pat_" + ("a" * 64)
PAT_B = "pat_" + ("b" * 64)


def test_usage_summary_request_accepts_alias_and_dedupes_fingerprints() -> None:
    request = UsageSummaryRequest.model_validate({"patFingerprints": [PAT_A, PAT_A, PAT_B]})

    assert request.pat_fingerprints == [PAT_A, PAT_A, PAT_B]
    assert dedupe_pat_fingerprints(request.pat_fingerprints) == [PAT_A, PAT_B]


def test_usage_summary_request_rejects_malformed_fingerprint() -> None:
    with pytest.raises(ValidationError):
        UsageSummaryRequest.model_validate({"patFingerprints": ["raw_pat_secret"]})


def test_usage_summary_row_serializes_browser_contract_aliases() -> None:
    last_used_at = datetime(2026, 4, 28, 10, tzinfo=UTC)

    row = UsageSummaryRow(
        patFingerprint=PAT_A,
        successfulSearchCount=3,
        last_used_at=last_used_at,
    )

    assert row.model_dump(mode="json", by_alias=True) == {
        "patFingerprint": PAT_A,
        "successfulSearchCount": 3,
        "lastUsedAt": "2026-04-28T10:00:00Z",
    }
