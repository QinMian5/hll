"""
Abstract: Unit tests enforcing Docker Compose naming and ownership conventions.
Out of scope: Container startup, image build behavior, and runtime health checks.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[5]
COMPOSE_DIR = REPO_ROOT / "infra" / "compose"
BASE_COMPOSE = COMPOSE_DIR / "docker-compose.base.yml"
DEV_COMPOSE = COMPOSE_DIR / "docker-compose.dev.yml"
PROD_COMPOSE = COMPOSE_DIR / "docker-compose.prod.yml"
TEST_COMPOSE = COMPOSE_DIR / "docker-compose.test.yml"
PROD_VOLUMES_HELPER = REPO_ROOT / "scripts" / "lib" / "prod-volumes.sh"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _top_level_name(path: Path) -> str | None:
    match = re.search(r"(?m)^name:\s*(\S+)\s*$", _read(path))
    if match is None:
        return None
    return match.group(1)


def _image_lines(path: Path) -> list[str]:
    return [line.strip() for line in _read(path).splitlines() if line.lstrip().startswith("image:")]


def _service_block(path: Path, service_name: str) -> str:
    content = _read(path)
    match = re.search(
        rf"(?ms)^  {re.escape(service_name)}:\n(?P<body>.*?)(?=^  [a-zA-Z0-9_-]+:|\Z)",
        content,
    )
    assert match is not None, f"{service_name} service must exist in {path}"
    return match.group("body")


def _compose_data(path: Path) -> dict[str, object]:
    return yaml.safe_load(_read(path))


def _service_data(path: Path, service_name: str) -> dict[str, object]:
    data = _compose_data(path)
    services = data["services"]
    assert isinstance(services, dict)
    service = services[service_name]
    assert isinstance(service, dict)
    return service


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
        "knowledge_logto_postgres_prod_data",
        "knowledge_corpus_postgres_prod_data",
        "source_pipeline_postgres_prod_data",
        "knowledge_redis_prod_data",
    ):
        assert f"name: {volume_name}" in prod


def test_prod_volume_helper_tracks_prod_compose_external_volumes() -> None:
    prod = _read(PROD_COMPOSE)
    helper = _read(PROD_VOLUMES_HELPER)

    external_volume_names = set(re.findall(r"(?m)^\s+name:\s+([a-z0-9_]+_prod_data)\s*$", prod))
    helper_volume_names = set(re.findall(r'"([a-z0-9_]+_prod_data)"', helper))

    assert helper_volume_names == external_volume_names


def test_dev_compose_keeps_orchestrator_out_of_default_startup() -> None:
    dev = _read(DEV_COMPOSE)

    assert "orchestrator:" in dev
    assert 'profiles: ["orchestrator"]' in dev
    assert "proxy" not in dev


def test_base_compose_defines_taxonomy_classification_runtime_with_job_queue_secret() -> None:
    runtime = _service_block(BASE_COMPOSE, "taxonomy_classification_runtime")

    assert 'command: ["/app/bin/run-taxonomy-classification-runtime.sh"]' in runtime
    assert "KNOWLEDGE_API_ROLE" not in runtime
    assert "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_QUEUE_NAME" in runtime
    assert "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_CLIENT_SECRET" in runtime
    assert "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_ALLOWED_CLIENT_ID" not in runtime


def test_base_compose_defines_taxonomy_classification_webhook_without_job_queue_secret() -> None:
    receiver = _service_block(BASE_COMPOSE, "taxonomy_classification_webhook_receiver")

    assert 'command: ["/app/bin/run-taxonomy-classification-webhook-receiver.sh"]' in receiver
    assert "KNOWLEDGE_API_ROLE" not in receiver
    assert "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_QUEUE_NAME" in receiver
    assert "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_ALLOWED_CLIENT_ID" in receiver
    assert "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_CLIENT_SECRET" not in receiver


def test_dev_compose_keeps_taxonomy_classification_services_out_of_default_startup() -> None:
    runtime = _service_block(DEV_COMPOSE, "taxonomy_classification_runtime")
    receiver = _service_block(DEV_COMPOSE, "taxonomy_classification_webhook_receiver")

    assert 'profiles: ["taxonomy_classification_runtime"]' in runtime
    assert 'profiles: ["taxonomy_classification_webhook_receiver"]' in receiver


def test_prod_keeps_api_off_public_edge_network() -> None:
    api_base = _service_data(BASE_COMPOSE, "api")
    api_prod = _service_data(PROD_COMPOSE, "api")

    assert api_base["networks"] == ["backend", "egress"]
    assert "networks" not in api_prod


def test_outbound_runtime_roles_use_dedicated_egress_network() -> None:
    base = _compose_data(BASE_COMPOSE)
    networks = base["networks"]
    assert isinstance(networks, dict)
    assert networks["backend"] == {"internal": True}
    assert networks["egress"] is None

    for service_name in ("api", "worker"):
        service = _service_data(BASE_COMPOSE, service_name)
        assert service["networks"] == ["backend", "egress"]

    for service_name in ("orchestrator", "taxonomy_classification_runtime"):
        service = _service_data(PROD_COMPOSE, service_name)
        assert service["networks"] == ["backend", "egress"]


def test_base_web_service_reaches_private_dependencies() -> None:
    web = _service_data(BASE_COMPOSE, "web")

    assert web["networks"] == ["backend", "edge"]
    assert set(web["depends_on"]) == {"api", "redis", "logto"}

    environment = web["environment"]
    assert isinstance(environment, dict)
    for key in (
        "KNOWLEDGE_WEB_INTERNAL_API_BASE_URL",
        "KNOWLEDGE_WEB_REDIS_URL",
        "KNOWLEDGE_WEB_LOGTO_ENDPOINT",
        "KNOWLEDGE_WEB_LOGTO_APP_ID",
        "KNOWLEDGE_WEB_LOGTO_APP_SECRET",
        "KNOWLEDGE_WEB_SESSION_SECRET",
        "KNOWLEDGE_WEB_QUOTA_REDIS_PREFIX",
        "KNOWLEDGE_WEB_QUOTA_ROUTE_OVERRIDES_JSON",
    ):
        assert key in environment


def test_prod_web_no_longer_exposes_browser_api_origin_config() -> None:
    web = _service_data(PROD_COMPOSE, "web")
    environment = web.get("environment", {})

    assert isinstance(environment, dict)
    assert "VITE_API_BASE_URL" not in environment
    assert "API_PROXY_TARGET" not in environment
