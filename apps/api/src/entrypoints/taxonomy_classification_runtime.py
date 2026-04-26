"""
Abstract: Long-running taxonomy-classification queue runtime entrypoint.
Out of scope: Docker Compose service definitions and webhook HTTP serving.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from core.config import (
    TaxonomyClassificationRuntimeSettings,
    load_taxonomy_classification_runtime_settings,
)
from modules.taxonomy_classification.job_queue_client import (
    TaxonomyClassificationJobQueueClient,
)
from modules.taxonomy_classification.job_queue_token import ClientCredentialsTokenProvider
from modules.taxonomy_classification.runtime import TaxonomyClassificationRuntimeService
from shared.db.session import build_async_engine, build_async_session_factory


@dataclass(slots=True, frozen=True)
class TaxonomyClassificationRuntime:
    settings: TaxonomyClassificationRuntimeSettings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    job_queue_client: TaxonomyClassificationJobQueueClient


def _required_setting(value: str | None, name: str) -> str:
    if value in (None, ""):
        raise RuntimeError(f"Expected taxonomy-classification setting {name} to be configured.")
    return value


def build_runtime() -> TaxonomyClassificationRuntime:
    settings = load_taxonomy_classification_runtime_settings()
    engine = build_async_engine(database_url=settings.database_url)
    session_factory = build_async_session_factory(engine=engine)
    return TaxonomyClassificationRuntime(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        job_queue_client=TaxonomyClassificationJobQueueClient(
            base_url=_required_setting(
                settings.taxonomy_classification_job_queue_base_url,
                "taxonomy_classification_job_queue_base_url",
            ),
            token_provider=ClientCredentialsTokenProvider(
                token_url=_required_setting(
                    settings.taxonomy_classification_job_queue_token_url,
                    "taxonomy_classification_job_queue_token_url",
                ),
                client_id=_required_setting(
                    settings.taxonomy_classification_job_queue_client_id,
                    "taxonomy_classification_job_queue_client_id",
                ),
                client_secret=_required_setting(
                    settings.taxonomy_classification_job_queue_client_secret,
                    "taxonomy_classification_job_queue_client_secret",
                ),
                resource=_required_setting(
                    settings.taxonomy_classification_job_queue_resource,
                    "taxonomy_classification_job_queue_resource",
                ),
                scope=settings.taxonomy_classification_job_queue_scopes,
            ),
        ),
    )


async def run_forever(runtime: TaxonomyClassificationRuntime) -> None:
    try:
        while True:
            async with runtime.session_factory() as session:
                service = TaxonomyClassificationRuntimeService(
                    session,
                    job_queue_client=runtime.job_queue_client,
                    poll_batch_size=runtime.settings.taxonomy_classification_poll_batch_size,
                    reconcile_interval_seconds=(
                        runtime.settings.taxonomy_classification_reconcile_interval_seconds
                    ),
                    reconcile_batch_size=(
                        runtime.settings.taxonomy_classification_reconcile_batch_size
                    ),
                )
                await service.tick()

            await asyncio.sleep(runtime.settings.taxonomy_classification_poll_interval_seconds)
    finally:
        await runtime.job_queue_client.aclose()
        await runtime.engine.dispose()


async def _async_main() -> None:
    runtime = build_runtime()
    await run_forever(runtime)


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
