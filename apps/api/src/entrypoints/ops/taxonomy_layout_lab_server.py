"""
Abstract: Local HTTP app for taxonomy card-scope layout tuning.
Out of scope: Production API router wiring and taxonomy persistence.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from typing import Any, cast

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from modules.taxonomy.dto import TaxonomyCardScopeLayout
from modules.taxonomy.layout import (
    TAXONOMY_CARD_SCOPE_LAYOUT_PRODUCTION_PARAMS,
    TaxonomyCardScopeLayoutParams,
)
from modules.taxonomy.layout_lab import (
    DEFAULT_LAYOUT_LAB_FIXTURE,
    LayoutLabFixtureNotFoundError,
    list_layout_lab_fixtures,
    solve_layout_lab_fixture,
)

LAYOUT_LAB_DEFAULT_PARAMS = replace(
    TAXONOMY_CARD_SCOPE_LAYOUT_PRODUCTION_PARAMS,
    simulation_ticks=10,
)


class LayoutLabSolveRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    fixture_name: str = Field(default=DEFAULT_LAYOUT_LAB_FIXTURE, alias="fixtureName")
    params: dict[str, Any] = Field(default_factory=dict)


def create_app() -> FastAPI:
    app = FastAPI(title="Taxonomy Layout Lab", docs_url=None, redoc_url=None)
    app.add_middleware(
        cast(Any, CORSMiddleware),
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.exception_handler(LayoutLabFixtureNotFoundError)
    async def handle_fixture_not_found(
        _request: Request,
        exc: LayoutLabFixtureNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.get("/fixtures")
    def fixtures() -> list[dict[str, Any]]:
        return [asdict(fixture) for fixture in list_layout_lab_fixtures()]

    @app.get("/params/default")
    def default_params() -> dict[str, Any]:
        return asdict(LAYOUT_LAB_DEFAULT_PARAMS)

    @app.post("/solve")
    def solve(request: LayoutLabSolveRequest) -> dict[str, Any]:
        layout = solve_layout_lab_fixture(
            fixture_name=request.fixture_name,
            params=_parse_params(request.params),
        )
        return _to_layout_slice_payload(layout=layout, fixture_name=request.fixture_name)

    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(create_app(), host=args.host, port=args.port)


def _parse_params(raw_params: dict[str, Any]) -> TaxonomyCardScopeLayoutParams:
    try:
        return TaxonomyCardScopeLayoutParams(**(asdict(LAYOUT_LAB_DEFAULT_PARAMS) | raw_params))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _to_layout_slice_payload(
    *,
    fixture_name: str,
    layout: TaxonomyCardScopeLayout,
) -> dict[str, Any]:
    return {
        "scope_kind": "taxonomy_node",
        "taxonomy_node_id": 1,
        "parent_taxonomy_node_id": None,
        "route_path": f"layout-lab/{fixture_name}",
        "layout_version": layout.layout_version,
        "layout_status": "ready",
        "requested_bounds": layout.world_bounds.model_dump(mode="json"),
        "nodes": [node.model_dump(mode="json") for node in layout.nodes],
        "edges": [
            [edge.source_node_id, edge.target_node_id, edge.strength] for edge in layout.edges
        ],
    }


if __name__ == "__main__":
    main()
