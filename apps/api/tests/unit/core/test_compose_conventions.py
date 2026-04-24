"""
Abstract: Unit tests enforcing Docker Compose naming and ownership conventions.
Out of scope: Container startup, image build behavior, and runtime health checks.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
COMPOSE_DIR = REPO_ROOT / "infra" / "compose"
BASE_COMPOSE = COMPOSE_DIR / "docker-compose.base.yml"
DEV_COMPOSE = COMPOSE_DIR / "docker-compose.dev.yml"
PROD_COMPOSE = COMPOSE_DIR / "docker-compose.prod.yml"
TEST_COMPOSE = COMPOSE_DIR / "docker-compose.test.yml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _top_level_name(path: Path) -> str | None:
    match = re.search(r"(?m)^name:\s*(\S+)\s*$", _read(path))
    if match is None:
        return None
    return match.group(1)


def _image_lines(path: Path) -> list[str]:
    return [line.strip() for line in _read(path).splitlines() if line.lstrip().startswith("image:")]


def test_environment_overlays_own_compose_project_names() -> None:
    assert _top_level_name(BASE_COMPOSE) is None
    assert _top_level_name(DEV_COMPOSE) == "knowledge-dev"
    assert _top_level_name(PROD_COMPOSE) == "knowledge-prod"
    assert _top_level_name(TEST_COMPOSE) == "knowledge-test"


def test_base_compose_does_not_pin_environment_specific_images() -> None:
    assert all(":dev" not in line for line in _image_lines(BASE_COMPOSE))
    assert all(":prod" not in line for line in _image_lines(BASE_COMPOSE))
    assert "image: redis:7-bookworm" in _image_lines(BASE_COMPOSE)


def test_base_compose_leaves_volume_and_network_names_to_environment_overlays() -> None:
    base = _read(BASE_COMPOSE)

    assert "name: knowledge_" not in base
    assert "name: source_pipeline_" not in base
    assert "name: knowledge_backend" not in base
    assert "name: knowledge_edge" not in base


def test_prod_compose_owns_all_external_prod_volume_names() -> None:
    prod = _read(PROD_COMPOSE)

    for volume_name in (
        "knowledge_postgres_prod_data",
        "knowledge_corpus_postgres_prod_data",
        "source_pipeline_postgres_prod_data",
        "knowledge_redis_prod_data",
    ):
        assert f"name: {volume_name}" in prod


def test_dev_compose_keeps_orchestrator_out_of_default_startup() -> None:
    dev = _read(DEV_COMPOSE)

    assert "orchestrator:" in dev
    assert 'profiles: ["orchestrator"]' in dev
    assert "proxy" not in dev
