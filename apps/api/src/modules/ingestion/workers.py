"""
Abstract: Ingestion job-processing primitives reused by worker entrypoints.
Out of scope: Dramatiq actor registration and runtime dependency assembly.
"""

from __future__ import annotations

from modules.knowledge_graph.ports import KnowledgeGraphWritePort
from shared.integrations import EmbeddingClientPort


async def process_ingestion_job(
    *,
    title: str,
    content: str,
    embedding_client: EmbeddingClientPort,
    knowledge_graph_write_port: KnowledgeGraphWritePort,
) -> int:
    embedding = await embedding_client.embed_text(content)
    return await knowledge_graph_write_port.materialize_card_from_ingestion(
        title=title,
        content=content,
        embedding=embedding,
    )
