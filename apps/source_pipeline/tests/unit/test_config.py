"""
Abstract: Unit tests for source-pipeline settings loading.
Out of scope: Database engine creation and runtime queue behavior.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from source_pipeline.config import SourcePipelineSettings


def test_source_pipeline_settings_require_explicit_urls() -> None:
    with pytest.raises(ValidationError):
        SourcePipelineSettings()

