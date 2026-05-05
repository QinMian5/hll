"""
Abstract: Local HTTP app for taxonomy card-scope layout tuning.
Out of scope: Production API router wiring and taxonomy persistence.
"""

from __future__ import annotations

import argparse
import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import asdict
from typing import Any, cast

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from modules.taxonomy.dto import TaxonomyCardScopeLayout
from modules.taxonomy.layout import TaxonomyCardScopeLayoutParams
from modules.taxonomy.layout_lab import (
    DEFAULT_LAYOUT_LAB_FIXTURE,
    LayoutLabFixtureNotFoundError,
    list_layout_lab_fixtures,
    solve_layout_lab_fixture,
)

LAYOUT_LAB_DEFAULT_PARAMS = TaxonomyCardScopeLayoutParams(
    seed_base_radius=80.0,
    seed_radius_step=96.0,
    simulation_ticks=160,
    alpha_min=0.001,
    velocity_retention=0.55,
    link_base_distance=92.0,
    link_distance_strength_factor=36.0,
    link_base_strength=1.05,
    link_strength_factor=0.5,
    charge_strength=-180.0,
    collision_radius=16.0,
    collision_strength=0.92,
    center_gravity_strength=0.10,
    radial_boundary_radius=0.0,
    radial_boundary_strength=0.0,
)


class LayoutLabSolveRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    fixture_name: str = Field(default=DEFAULT_LAYOUT_LAB_FIXTURE, alias="fixtureName")
    params: dict[str, Any] = Field(default_factory=dict)


def create_app() -> FastAPI:
    app = FastAPI(title="Taxonomy Layout Lab", docs_url=None, redoc_url=None)
    solve_cache = _SolveResultCache()
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
        params = _parse_params(request.params)
        return solve_cache.get_or_build(
            key=_solve_cache_key(fixture_name=request.fixture_name, params=params),
            build=lambda: _solve_layout_payload(
                fixture_name=request.fixture_name,
                params=params,
            ),
        )

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


def _solve_layout_payload(
    *,
    fixture_name: str,
    params: TaxonomyCardScopeLayoutParams,
) -> dict[str, Any]:
    layout = solve_layout_lab_fixture(
        fixture_name=fixture_name,
        params=params,
    )
    return _to_layout_slice_payload(layout=layout, fixture_name=fixture_name)


def _solve_cache_key(
    *,
    fixture_name: str,
    params: TaxonomyCardScopeLayoutParams,
) -> tuple[str, tuple[tuple[str, Any], ...]]:
    return fixture_name, tuple(sorted(asdict(params).items()))


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


class _InFlightSolve:
    def __init__(self) -> None:
        self.event = threading.Event()
        self.error: Exception | None = None
        self.result: dict[str, Any] | None = None


class _SolveResultCache:
    def __init__(self, max_entries: int = 64) -> None:
        self._max_entries = max_entries
        self._lock = threading.Lock()
        self._results: OrderedDict[tuple[str, tuple[tuple[str, Any], ...]], dict[str, Any]] = (
            OrderedDict()
        )
        self._inflight: dict[tuple[str, tuple[tuple[str, Any], ...]], _InFlightSolve] = {}

    def get_or_build(
        self,
        *,
        key: tuple[str, tuple[tuple[str, Any], ...]],
        build: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        with self._lock:
            cached_result = self._results.get(key)
            if cached_result is not None:
                self._results.move_to_end(key)
                return cached_result

            in_flight = self._inflight.get(key)
            should_build = in_flight is None
            if in_flight is None:
                in_flight = _InFlightSolve()
                self._inflight[key] = in_flight

        if not should_build:
            in_flight.event.wait()
            if in_flight.error is not None:
                raise in_flight.error
            if in_flight.result is None:
                raise RuntimeError("Layout lab solve completed without a result.")
            return in_flight.result

        try:
            result = build()
        except Exception as exc:
            with self._lock:
                in_flight.error = exc
                self._inflight.pop(key, None)
                in_flight.event.set()
            raise

        with self._lock:
            in_flight.result = result
            self._results[key] = result
            self._results.move_to_end(key)
            while len(self._results) > self._max_entries:
                self._results.popitem(last=False)
            self._inflight.pop(key, None)
            in_flight.event.set()

        return result


if __name__ == "__main__":
    main()
