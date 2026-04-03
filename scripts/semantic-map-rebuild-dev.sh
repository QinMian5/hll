#!/usr/bin/env bash
# abstract: Run one semantic-map rebuild against the local API runtime environment.
# out_of_scope: HTTP trigger exposure and continuous scheduling.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"

uv --directory "$API_DIR" run python - <<'PY'
from __future__ import annotations

import asyncio

from entrypoints.runtime import get_runtime_dependencies
from modules.knowledge_graph.builders import build_knowledge_graph_service
from modules.semantic_map.builders import build_semantic_map_rebuild_service


async def _main() -> None:
    runtime = get_runtime_dependencies()
    async with runtime.session_factory() as session:
        knowledge_graph_service = build_knowledge_graph_service(
            session=session,
            edge_similarity_top_k=runtime.settings.edge_similarity_top_k,
            edge_similarity_min_strength=runtime.settings.edge_similarity_min_strength,
        )
        rebuild_service = build_semantic_map_rebuild_service(
            session=session,
            projection_port=knowledge_graph_service,
        )
        version = await rebuild_service.rebuild_current_snapshot()
        if version is None:
            print("semantic-map rebuild skipped: no knowledge nodes available")
            return
        print(f"semantic-map rebuild published version={version}")


asyncio.run(_main())
PY
