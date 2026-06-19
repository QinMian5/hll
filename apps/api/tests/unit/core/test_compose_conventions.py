"""
Abstract: Unit tests enforcing Docker Compose naming, ownership, and health-check conventions.
Out of scope: Container startup and image build behavior.
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
NGINX_CONF = REPO_ROOT / "infra" / "docker" / "nginx" / "default.conf"
NGINX_DOCKERFILE = REPO_ROOT / "infra" / "docker" / "nginx" / "Dockerfile"
PROD_VOLUMES_HELPER = REPO_ROOT / "scripts" / "lib" / "prod-volumes.sh"
POSTGRES_ROLE_INIT = REPO_ROOT / "infra" / "docker" / "postgres" / "init" / "10-roles.sh"
POSTGRES_ROLE_BOOTSTRAP = REPO_ROOT / "scripts" / "lib" / "postgres-role-bootstrap.sh"
SCRIPT_DIR = REPO_ROOT / "scripts"
DEV_UP_SCRIPT = SCRIPT_DIR / "dev-up.sh"
PROD_UP_SCRIPT = SCRIPT_DIR / "prod-up.sh"
MCP_RUN_SCRIPT = REPO_ROOT / "infra" / "docker" / "mcp" / "run-mcp.sh"
TAXONOMY_VIEW_LAYOUT_RUN_SCRIPT = (
    REPO_ROOT / "infra" / "docker" / "api" / "run-taxonomy-view-layout-runtime.sh"
)
TAXONOMY_LAYOUT_PRECOMPUTE_SCRIPT = REPO_ROOT / "scripts" / "taxonomy-layout-precompute.sh"
TAXONOMY_LAYOUT_PRECOMPUTE_COMPOSE = (
    COMPOSE_DIR / "docker-compose.taxonomy-layout-precompute.yml"
)
RESOURCE_FIELDS = ("mem_limit", "memswap_limit", "cpus", "pids_limit")
EXPECTED_PROD_RESOURCE_BUDGETS = {
    "postgres": {"mem_limit": "1536m", "memswap_limit": "1536m", "cpus": 1.5, "pids_limit": 256},
    "knowledge_corpus_db": {
        "mem_limit": "1024m",
        "memswap_limit": "1024m",
        "cpus": 1.0,
        "pids_limit": 192,
    },
    "source_pipeline_db": {
        "mem_limit": "768m",
        "memswap_limit": "768m",
        "cpus": 0.75,
        "pids_limit": 192,
    },
    "mcp_db": {"mem_limit": "512m", "memswap_limit": "512m", "cpus": 0.5, "pids_limit": 128},
    "logto-postgres": {
        "mem_limit": "512m",
        "memswap_limit": "512m",
        "cpus": 0.5,
        "pids_limit": 128,
    },
    "redis": {"mem_limit": "256m", "memswap_limit": "256m", "cpus": 0.5, "pids_limit": 128},
    "api": {"mem_limit": "768m", "memswap_limit": "768m", "cpus": 1.0, "pids_limit": 256},
    "worker": {"mem_limit": "1536m", "memswap_limit": "1536m", "cpus": 2.0, "pids_limit": 512},
    "taxonomy_view_layout_runtime": {
        "mem_limit": "512m",
        "memswap_limit": "512m",
        "cpus": 1.0,
        "pids_limit": 128,
    },
    "taxonomy_classification_runtime": {
        "mem_limit": "768m",
        "memswap_limit": "768m",
        "cpus": 1.0,
        "pids_limit": 256,
    },
    "taxonomy_classification_webhook_receiver": {
        "mem_limit": "384m",
        "memswap_limit": "384m",
        "cpus": 0.5,
        "pids_limit": 128,
    },
    "mcp": {"mem_limit": "512m", "memswap_limit": "512m", "cpus": 0.75, "pids_limit": 128},
    "orchestrator": {"mem_limit": "384m", "memswap_limit": "384m", "cpus": 0.75, "pids_limit": 128},
    "source_pipeline_webhook_receiver": {
        "mem_limit": "384m",
        "memswap_limit": "384m",
        "cpus": 0.5,
        "pids_limit": 128,
    },
    "web": {"mem_limit": "1024m", "memswap_limit": "1024m", "cpus": 0.75, "pids_limit": 128},
    "logto": {"mem_limit": "768m", "memswap_limit": "768m", "cpus": 0.75, "pids_limit": 128},
    "nginx": {"mem_limit": "128m", "memswap_limit": "128m", "cpus": 0.25, "pids_limit": 64},
    "cloudflare-ingress": {
        "mem_limit": "128m",
        "memswap_limit": "128m",
        "cpus": 0.25,
        "pids_limit": 64,
    },
}
EXPECTED_DEV_RESOURCE_BUDGETS = {
    "postgres": {"mem_limit": "768m", "memswap_limit": "768m", "cpus": 0.75, "pids_limit": 192},
    "knowledge_corpus_db": {
        "mem_limit": "768m",
        "memswap_limit": "768m",
        "cpus": 0.75,
        "pids_limit": 192,
    },
    "source_pipeline_db": {
        "mem_limit": "512m",
        "memswap_limit": "512m",
        "cpus": 0.5,
        "pids_limit": 128,
    },
    "mcp_db": {"mem_limit": "384m", "memswap_limit": "384m", "cpus": 0.5, "pids_limit": 128},
    "logto-postgres": {
        "mem_limit": "384m",
        "memswap_limit": "384m",
        "cpus": 0.5,
        "pids_limit": 128,
    },
    "redis": {"mem_limit": "192m", "memswap_limit": "192m", "cpus": 0.25, "pids_limit": 96},
    "api": {"mem_limit": "512m", "memswap_limit": "512m", "cpus": 0.75, "pids_limit": 192},
    "worker": {"mem_limit": "1024m", "memswap_limit": "1024m", "cpus": 1.0, "pids_limit": 384},
    "taxonomy_view_layout_runtime": {
        "mem_limit": "384m",
        "memswap_limit": "384m",
        "cpus": 0.75,
        "pids_limit": 128,
    },
    "mcp": {"mem_limit": "384m", "memswap_limit": "384m", "cpus": 0.5, "pids_limit": 128},
    "web": {"mem_limit": "1024m", "memswap_limit": "1024m", "cpus": 0.5, "pids_limit": 128},
    "logto": {"mem_limit": "512m", "memswap_limit": "512m", "cpus": 0.5, "pids_limit": 128},
}


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


def _assert_resource_budget(path: Path, expected: dict[str, dict[str, object]]) -> None:
    for service_name, expected_budget in expected.items():
        service = _service_data(path, service_name)
        for field_name in RESOURCE_FIELDS:
            assert service.get(field_name) == expected_budget[field_name], service_name


def test_environment_overlays_own_compose_project_names() -> None:
    assert _top_level_name(BASE_COMPOSE) is None
    assert _top_level_name(DEV_COMPOSE) == "knowledge-dev"
    assert _top_level_name(PROD_COMPOSE) == "knowledge-prod"
    assert _top_level_name(TEST_COMPOSE) == "knowledge-test"


def test_dev_migration_scripts_do_not_override_compose_project_name() -> None:
    for script_name in (
        "alembic-autogen.sh",
        "alembic-upgrade-dev.sh",
    ):
        script = _read(SCRIPT_DIR / script_name)

        assert "DEV_COMPOSE_PROJECT" not in script
        assert '\n  -p "' not in script


def test_stack_start_scripts_clear_all_one_shot_migration_jobs() -> None:
    for path in (DEV_UP_SCRIPT, PROD_UP_SCRIPT):
        script = _read(path)

        for service_name in (
            "migrate",
            "knowledge_corpus_migrate",
            "source_pipeline_migrate",
            "mcp_migrate",
        ):
            assert re.search(rf"docker compose [^\n]*\brm\b[^\n]*\b{service_name}\b", script)
            assert re.search(rf"docker compose [^\n]*\blogs\b[^\n]*\b{service_name}\b", script)


def test_stack_start_scripts_converge_postgres_roles_before_migrations() -> None:
    bootstrap_helper = _read(POSTGRES_ROLE_BOOTSTRAP)
    assert re.search(r"docker compose [^\n]*\bup\b[^\n]*--wait postgres", bootstrap_helper)
    assert "exec -T postgres /docker-entrypoint-initdb.d/10-roles.sh" in bootstrap_helper

    for path in (DEV_UP_SCRIPT, PROD_UP_SCRIPT):
        script = _read(path)

        assert "scripts/lib/postgres-role-bootstrap.sh" in script
        assert 'converge_online_postgres_roles "${compose_args[@]}"' in script


def test_makefile_exposes_environment_scoped_alembic_entries_only() -> None:
    makefile = _read(REPO_ROOT / "Makefile")

    assert "alembic-autogen:" in makefile
    assert "alembic-upgrade-dev:" in makefile
    assert "alembic-upgrade-test:" in makefile
    assert "alembic-upgrade-prod:" in makefile
    assert "mcp-alembic" not in makefile


def test_repository_does_not_expose_app_specific_alembic_scripts() -> None:
    for script_name in (
        "knowledge-corpus-alembic-autogen.sh",
        "knowledge-corpus-alembic-upgrade-dev.sh",
        "knowledge-corpus-alembic-upgrade-test.sh",
        "knowledge-corpus-alembic-upgrade-prod.sh",
        "source-pipeline-alembic-autogen.sh",
        "source-pipeline-alembic-upgrade-dev.sh",
        "source-pipeline-alembic-upgrade-test.sh",
        "source-pipeline-alembic-upgrade-prod.sh",
        "mcp-alembic-autogen.sh",
        "mcp-alembic-upgrade-dev.sh",
        "mcp-alembic-upgrade-test.sh",
        "mcp-alembic-upgrade-prod.sh",
    ):
        assert not (SCRIPT_DIR / script_name).exists()


def test_test_compose_migration_services_use_explicit_alembic_commands() -> None:
    expected_commands = {
        "knowledge_corpus_migrate": [
            "alembic",
            "-c",
            "/app/apps/knowledge_corpus/alembic.ini",
            "upgrade",
            "head",
        ],
        "source_pipeline_migrate": [
            "alembic",
            "-c",
            "/app/apps/source_pipeline/alembic.ini",
            "upgrade",
            "head",
        ],
        "mcp_migrate": [
            "alembic",
            "-c",
            "/app/apps/mcp/alembic.ini",
            "upgrade",
            "head",
        ],
    }

    for service_name, expected_command in expected_commands.items():
        service = _service_data(TEST_COMPOSE, service_name)
        assert service["command"] == expected_command


def test_base_compose_does_not_pin_environment_specific_images() -> None:
    assert all(":dev" not in line for line in _image_lines(BASE_COMPOSE))
    assert all(":prod" not in line for line in _image_lines(BASE_COMPOSE))
    assert "image: redis:7-bookworm" in _image_lines(BASE_COMPOSE)


def test_compose_services_do_not_disable_oom_kills() -> None:
    for compose_file in (BASE_COMPOSE, DEV_COMPOSE, PROD_COMPOSE):
        data = _compose_data(compose_file)
        services = data["services"]
        assert isinstance(services, dict)

        for service in services.values():
            assert isinstance(service, dict)
            assert "oom_kill_disable" not in service


def test_base_redis_uses_bounded_noeviction_memory_policy() -> None:
    redis = _service_data(BASE_COMPOSE, "redis")

    assert redis["command"] == [
        "redis-server",
        "--save",
        "",
        "--appendonly",
        "no",
        "--maxmemory",
        "192mb",
        "--maxmemory-policy",
        "noeviction",
    ]


def test_prod_compose_defines_resource_budgets_for_long_running_services() -> None:
    _assert_resource_budget(PROD_COMPOSE, EXPECTED_PROD_RESOURCE_BUDGETS)


def test_dev_compose_defines_resource_budgets_for_long_running_services() -> None:
    _assert_resource_budget(DEV_COMPOSE, EXPECTED_DEV_RESOURCE_BUDGETS)


def test_base_compose_defines_web_healthcheck() -> None:
    web = _service_data(BASE_COMPOSE, "web")

    assert web["healthcheck"] == {
        "test": [
            "CMD",
            "node",
            "-e",
            "require('http').get('http://127.0.0.1:5173/', (response) => "
            "process.exit(response.statusCode && response.statusCode >= 200 && "
            "response.statusCode < 400 ? 0 : 1)).on('error', () => process.exit(1))",
        ],
        "interval": "10s",
        "timeout": "5s",
        "retries": 6,
        "start_period": "10s",
    }


def test_base_compose_leaves_volume_and_network_names_to_environment_overlays() -> None:
    base = _read(BASE_COMPOSE)

    assert "name: knowledge_" not in base
    assert "name: source_pipeline_" not in base
    assert "name: knowledge_backend" not in base
    assert "name: knowledge_edge" not in base


def test_base_compose_uses_networks_instead_of_expose_metadata() -> None:
    base = _read(BASE_COMPOSE)

    assert "ports:" not in base
    assert "expose:" not in base


def test_prod_compose_owns_all_external_prod_volume_names() -> None:
    prod = _read(PROD_COMPOSE)

    for volume_name in (
        "knowledge_postgres_prod_data",
        "knowledge_logto_postgres_prod_data",
        "knowledge_corpus_postgres_prod_data",
        "source_pipeline_postgres_prod_data",
        "knowledge_mcp_postgres_prod_data",
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


def test_logto_admin_container_port_is_fixed_and_dev_publishes_host_port() -> None:
    base_logto = _service_data(BASE_COMPOSE, "logto")
    base_seed = _service_data(BASE_COMPOSE, "logto-seed")
    dev_logto = _service_data(DEV_COMPOSE, "logto")
    dev_seed = _service_data(DEV_COMPOSE, "logto-seed")

    for service in (base_logto, base_seed):
        environment = service["environment"]
        assert isinstance(environment, dict)
        assert environment["ADMIN_PORT"] == "3002"

    assert dev_logto["ports"] == [
        "3011:3001",
        "3012:3002",
    ]
    assert dev_logto["extra_hosts"] == [
        "knowledge-dev-logto.localhost:host-gateway",
        "knowledge-dev-logto-admin.localhost:host-gateway",
    ]
    assert dev_seed["extra_hosts"] == dev_logto["extra_hosts"]


def test_base_compose_defines_taxonomy_classification_runtime_with_job_queue_secret() -> None:
    runtime = _service_block(BASE_COMPOSE, "taxonomy_classification_runtime")

    assert 'command: ["/app/bin/run-taxonomy-classification-runtime.sh"]' in runtime
    assert "KNOWLEDGE_API_ROLE" not in runtime
    assert "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_QUEUE_NAME" in runtime
    assert "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_CLIENT_SECRET" in runtime
    assert "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CONTINUATION_REQUEST_BATCH_SIZE" in runtime
    assert "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CONTINUATION_FLUSH_INTERVAL_SECONDS" in runtime
    assert "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_PROJECTION_REFRESH_BATCH_SIZE" in runtime
    assert "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_ALLOWED_CLIENT_ID" not in runtime


def test_base_compose_defines_taxonomy_classification_webhook_without_job_queue_secret() -> None:
    receiver = _service_block(BASE_COMPOSE, "taxonomy_classification_webhook_receiver")

    assert 'command: ["/app/bin/run-taxonomy-classification-webhook-receiver.sh"]' in receiver
    assert "KNOWLEDGE_API_ROLE" not in receiver
    assert "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_QUEUE_NAME" in receiver
    assert "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_ALLOWED_CLIENT_ID" in receiver
    assert "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_CLIENT_SECRET" not in receiver


def test_base_compose_defines_taxonomy_view_layout_runtime_with_private_dependencies() -> None:
    runtime = _service_data(BASE_COMPOSE, "taxonomy_view_layout_runtime")

    assert runtime["command"] == ["/app/bin/run-taxonomy-view-layout-runtime.sh"]
    assert runtime["networks"] == ["backend"]
    assert runtime["depends_on"] == {
        "postgres": {"condition": "service_healthy"},
        "redis": {"condition": "service_healthy"},
        "migrate": {"condition": "service_completed_successfully"},
    }

    environment = runtime["environment"]
    assert isinstance(environment, dict)
    for key in (
        "KNOWLEDGE_API_DATABASE_URL",
        "KNOWLEDGE_API_REDIS_URL",
        "KNOWLEDGE_API_TAXONOMY_VIEW_CACHE_TTL_SECONDS",
        "KNOWLEDGE_API_EDGE_TITLE_MENTION_TOP_K",
        "KNOWLEDGE_API_EDGE_SEMANTIC_TOP_K",
        "KNOWLEDGE_API_EDGE_SEMANTIC_MIN_STRENGTH",
        "KNOWLEDGE_API_EDGE_SEMANTIC_CANDIDATE_LIMIT",
    ):
        assert key in environment
    assert "KNOWLEDGE_API_EMBEDDING_API_KEY" not in environment


def test_base_compose_uses_current_edge_initialization_env_contract() -> None:
    expected_edge_keys = {
        "KNOWLEDGE_API_EDGE_TITLE_MENTION_TOP_K",
        "KNOWLEDGE_API_EDGE_SEMANTIC_TOP_K",
        "KNOWLEDGE_API_EDGE_SEMANTIC_MIN_STRENGTH",
        "KNOWLEDGE_API_EDGE_SEMANTIC_CANDIDATE_LIMIT",
    }
    retired_edge_keys = {
        "KNOWLEDGE_API_EDGE_SIMILARITY_TOP_K",
        "KNOWLEDGE_API_EDGE_SIMILARITY_MIN_STRENGTH",
    }

    for service_name in ("api", "worker", "taxonomy_view_layout_runtime"):
        service = _service_data(BASE_COMPOSE, service_name)
        environment = service["environment"]
        assert isinstance(environment, dict)

        assert expected_edge_keys <= set(environment)
        assert retired_edge_keys.isdisjoint(environment)


def test_base_api_service_passes_taxonomy_view_cache_ttl_env_contract() -> None:
    api = _service_data(BASE_COMPOSE, "api")
    environment = api["environment"]

    assert isinstance(environment, dict)
    assert "KNOWLEDGE_API_SEARCH_VECTOR_CANDIDATE_POOL_SIZE" in environment
    assert "KNOWLEDGE_API_SEARCH_RESPONSE_CACHE_TTL_SECONDS" in environment
    assert "KNOWLEDGE_API_SEARCH_EMBEDDING_CACHE_TTL_SECONDS" in environment
    assert "KNOWLEDGE_API_TAXONOMY_VIEW_CACHE_TTL_SECONDS" in environment


def test_base_worker_service_passes_required_cache_ttl_env_contract() -> None:
    worker = _service_data(BASE_COMPOSE, "worker")
    environment = worker["environment"]

    assert isinstance(environment, dict)
    assert "KNOWLEDGE_API_SEARCH_VECTOR_CANDIDATE_POOL_SIZE" in environment
    assert "KNOWLEDGE_API_SEARCH_RESPONSE_CACHE_TTL_SECONDS" in environment
    assert "KNOWLEDGE_API_SEARCH_EMBEDDING_CACHE_TTL_SECONDS" in environment


def test_base_api_and_worker_services_pass_required_shared_runtime_env_contract() -> None:
    required_keys = {
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CURSOR_COMMAND",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CURSOR_WORKSPACE_ROOT",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CURSOR_TIMEOUT_SECONDS",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CURSOR_MAX_RETRIES",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_MAX_WORKERS",
    }

    for service_name in ("api", "worker"):
        service = _service_data(BASE_COMPOSE, service_name)
        environment = service["environment"]

        assert isinstance(environment, dict)
        assert required_keys <= set(environment)


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


def test_prod_compose_uses_project_owned_cloudflare_tunnel_ingress() -> None:
    prod = _compose_data(PROD_COMPOSE)
    services = prod["services"]
    assert isinstance(services, dict)
    assert "cloudflare-ingress" in services

    ingress = services["cloudflare-ingress"]
    assert isinstance(ingress, dict)
    assert ingress["image"] == "cloudflare/cloudflared:latest"
    assert ingress["command"] == ["tunnel", "--no-autoupdate", "--protocol", "http2", "run"]
    assert ingress["environment"] == {
        "TUNNEL_TOKEN": "${CLOUDFLARE_TUNNEL_TOKEN:?CLOUDFLARE_TUNNEL_TOKEN is required}",
    }
    assert ingress["depends_on"] == {"nginx": {"condition": "service_healthy"}}
    assert ingress["networks"] == ["edge", "egress"]
    assert ingress["restart"] == "unless-stopped"

    nginx = services["nginx"]
    assert isinstance(nginx, dict)
    assert nginx["networks"] == ["edge"]
    assert "proxy" not in prod.get("networks", {})


def test_base_web_service_reaches_private_dependencies() -> None:
    web = _service_data(BASE_COMPOSE, "web")

    assert web["networks"] == ["backend", "edge"]
    assert set(web["depends_on"]) == {"api", "redis", "logto", "mcp"}

    environment = web["environment"]
    assert isinstance(environment, dict)
    assert "KNOWLEDGE_WEB_HOST" not in environment
    assert "KNOWLEDGE_WEB_PORT" not in environment
    for key in (
        "KNOWLEDGE_WEB_INTERNAL_API_BASE_URL",
        "KNOWLEDGE_WEB_REDIS_URL",
        "KNOWLEDGE_WEB_LOGTO_ENDPOINT",
        "KNOWLEDGE_WEB_LOGTO_APP_ID",
        "KNOWLEDGE_WEB_LOGTO_APP_SECRET",
        "KNOWLEDGE_WEB_LOGTO_MANAGEMENT_API_BASE_URL",
        "KNOWLEDGE_WEB_LOGTO_MANAGEMENT_TOKEN_URL",
        "KNOWLEDGE_WEB_LOGTO_MANAGEMENT_RESOURCE",
        "KNOWLEDGE_WEB_LOGTO_MANAGEMENT_SCOPES",
        "KNOWLEDGE_WEB_LOGTO_MANAGEMENT_CLIENT_ID",
        "KNOWLEDGE_WEB_LOGTO_MANAGEMENT_CLIENT_SECRET",
        "KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_BASE_URL",
        "KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_TOKEN_URL",
        "KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_RESOURCE",
        "KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_SCOPES",
        "KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_CLIENT_ID",
        "KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_CLIENT_SECRET",
        "KNOWLEDGE_WEB_PAT_FINGERPRINT_SECRET",
        "KNOWLEDGE_WEB_SESSION_SECRET",
        "KNOWLEDGE_WEB_QUOTA_REDIS_PREFIX",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_ANON_BURST_LIMIT",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_ANON_BURST_WINDOW_SECONDS",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_ANON_TOTAL_LIMIT",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_ANON_TOTAL_WINDOW_SECONDS",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_AUTH_BURST_LIMIT",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_AUTH_BURST_WINDOW_SECONDS",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_AUTH_TOTAL_LIMIT",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_AUTH_TOTAL_WINDOW_SECONDS",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_IP_BURST_LIMIT",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_IP_BURST_WINDOW_SECONDS",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_IP_TOTAL_LIMIT",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_IP_TOTAL_WINDOW_SECONDS",
    ):
        assert key in environment
    assert "KNOWLEDGE_WEB_QUOTA_ROUTE_OVERRIDES_JSON" not in environment


def test_base_mcp_service_defines_internal_usage_summary_auth() -> None:
    mcp = _service_data(BASE_COMPOSE, "mcp")
    environment = mcp["environment"]

    assert isinstance(environment, dict)
    for key in (
        "KNOWLEDGE_MCP_USAGE_SUMMARY_AUTH_RESOURCE",
        "KNOWLEDGE_MCP_USAGE_SUMMARY_REQUIRED_SCOPE",
        "KNOWLEDGE_MCP_USAGE_SUMMARY_ALLOWED_CLIENT_ID",
        "KNOWLEDGE_MCP_USAGE_SUMMARY_MAX_BATCH_SIZE",
    ):
        assert key in environment


def test_prod_web_no_longer_exposes_browser_api_origin_config() -> None:
    web = _service_data(PROD_COMPOSE, "web")
    environment = web.get("environment", {})

    assert isinstance(environment, dict)
    assert "VITE_API_BASE_URL" not in environment
    assert "API_PROXY_TARGET" not in environment


def test_dev_and_prod_web_set_explicit_node_env() -> None:
    dev_web = _service_data(DEV_COMPOSE, "web")
    prod_web = _service_data(PROD_COMPOSE, "web")

    assert dev_web["environment"] == {"NODE_ENV": "development"}
    assert prod_web["environment"] == {"NODE_ENV": "production"}


def test_dev_and_prod_compose_define_taxonomy_view_layout_runtime_image() -> None:
    dev_runtime = _service_data(DEV_COMPOSE, "taxonomy_view_layout_runtime")
    prod_runtime = _service_data(PROD_COMPOSE, "taxonomy_view_layout_runtime")

    assert dev_runtime["image"] == "knowledge-api:dev"
    assert prod_runtime["image"] == "knowledge-api:prod"


def test_online_postgres_init_does_not_bootstrap_mcp_role_or_schema() -> None:
    script = _read(POSTGRES_ROLE_INIT)

    assert "MCP_DB_USER" not in script
    assert "MCP_DB_PASSWORD" not in script
    assert "CREATE SCHEMA IF NOT EXISTS mcp_usage" not in script
    assert "GRANT USAGE ON SCHEMA mcp_usage" not in script
    assert "IN SCHEMA mcp_usage" not in script


def test_base_compose_defines_mcp_migration_service() -> None:
    mcp_db = _service_data(BASE_COMPOSE, "mcp_db")
    assert mcp_db["build"]["dockerfile"] == "infra/docker/postgres/Dockerfile"
    assert mcp_db["volumes"] == ["knowledge_mcp_postgres_data:/var/lib/postgresql"]
    assert mcp_db["networks"] == ["backend"]

    mcp_db_environment = mcp_db["environment"]
    assert isinstance(mcp_db_environment, dict)
    assert mcp_db_environment["POSTGRES_DB"] == (
        "${KNOWLEDGE_MCP_POSTGRES_DB:?KNOWLEDGE_MCP_POSTGRES_DB is required}"
    )
    assert mcp_db_environment["APP_DB_USER"] == (
        "${KNOWLEDGE_MCP_DB_USER:?KNOWLEDGE_MCP_DB_USER is required}"
    )
    assert mcp_db_environment["MIGRATION_DB_USER"] == (
        "${KNOWLEDGE_MCP_MIGRATION_DB_USER:?KNOWLEDGE_MCP_MIGRATION_DB_USER is required}"
    )

    mcp_migrate = _service_data(BASE_COMPOSE, "mcp_migrate")

    assert mcp_migrate["build"]["dockerfile"] == "infra/docker/mcp/Dockerfile"
    assert mcp_migrate["command"] == [
        "alembic",
        "-c",
        "/app/apps/mcp/alembic.ini",
        "upgrade",
        "head",
    ]
    assert mcp_migrate["networks"] == ["backend"]
    assert mcp_migrate["depends_on"] == {"mcp_db": {"condition": "service_healthy"}}

    environment = mcp_migrate["environment"]
    assert isinstance(environment, dict)
    assert environment["KNOWLEDGE_MCP_MIGRATION_DATABASE_URL"] == (
        "${KNOWLEDGE_MCP_MIGRATION_DATABASE_URL:?KNOWLEDGE_MCP_MIGRATION_DATABASE_URL is required}"
    )


def test_base_compose_defines_public_mcp_service_with_private_dependencies() -> None:
    mcp = _service_data(BASE_COMPOSE, "mcp")

    assert mcp["build"]["dockerfile"] == "infra/docker/mcp/Dockerfile"
    assert mcp["command"] == ["/app/bin/run-mcp.sh"]
    assert mcp["networks"] == ["backend", "edge"]
    assert "expose" not in mcp
    assert set(mcp["depends_on"]) == {"api", "redis", "mcp_db", "mcp_migrate", "logto"}

    environment = mcp["environment"]
    assert isinstance(environment, dict)
    assert "KNOWLEDGE_MCP_HOST" not in environment
    assert "KNOWLEDGE_MCP_PORT" not in environment
    for key in (
        "KNOWLEDGE_MCP_PUBLIC_BASE_URL",
        "KNOWLEDGE_MCP_INTERNAL_API_BASE_URL",
        "KNOWLEDGE_MCP_REDIS_URL",
        "KNOWLEDGE_MCP_DATABASE_URL",
        "KNOWLEDGE_MCP_LOGTO_ISSUER",
        "KNOWLEDGE_MCP_LOGTO_DISCOVERY_URL",
        "KNOWLEDGE_MCP_LOGTO_TOKEN_URL",
        "KNOWLEDGE_MCP_LOGTO_RESOURCE",
        "KNOWLEDGE_MCP_LOGTO_TOKEN_EXCHANGE_CLIENT_ID",
        "KNOWLEDGE_MCP_LOGTO_TOKEN_EXCHANGE_CLIENT_SECRET",
        "KNOWLEDGE_MCP_PAT_FINGERPRINT_SECRET",
        "KNOWLEDGE_MCP_ALLOWED_ORIGINS",
        "KNOWLEDGE_MCP_USER_DAILY_LIMIT",
        "KNOWLEDGE_MCP_USER_DAILY_WINDOW_SECONDS",
        "KNOWLEDGE_MCP_USER_WEEKLY_LIMIT",
        "KNOWLEDGE_MCP_USER_WEEKLY_WINDOW_SECONDS",
    ):
        assert key in environment


def test_compose_files_do_not_define_environment_variable_defaults() -> None:
    default_substitution_pattern = re.compile(r"\$\{[A-Z0-9_]+:-")

    for compose_file in (BASE_COMPOSE, DEV_COMPOSE, PROD_COMPOSE, TEST_COMPOSE):
        assert default_substitution_pattern.search(_read(compose_file)) is None


def test_env_example_owns_compose_default_values() -> None:
    required_quota_keys = (
        "KNOWLEDGE_MCP_USER_DAILY_LIMIT",
        "KNOWLEDGE_MCP_USER_DAILY_WINDOW_SECONDS",
        "KNOWLEDGE_MCP_USER_WEEKLY_LIMIT",
        "KNOWLEDGE_MCP_USER_WEEKLY_WINDOW_SECONDS",
    )
    removed_quota_keys = (
        "KNOWLEDGE_MCP_USER_BURST_LIMIT",
        "KNOWLEDGE_MCP_USER_BURST_WINDOW_SECONDS",
        "KNOWLEDGE_MCP_USER_TOTAL_LIMIT",
        "KNOWLEDGE_MCP_USER_TOTAL_WINDOW_SECONDS",
        "KNOWLEDGE_MCP_PAT_BURST_LIMIT",
        "KNOWLEDGE_MCP_PAT_BURST_WINDOW_SECONDS",
        "KNOWLEDGE_MCP_PAT_TOTAL_LIMIT",
        "KNOWLEDGE_MCP_PAT_TOTAL_WINDOW_SECONDS",
    )
    removed_topology_keys = (
        "KNOWLEDGE_LOGTO_ADMIN_PORT",
        "KNOWLEDGE_MCP_HOST",
        "KNOWLEDGE_MCP_PORT",
        "KNOWLEDGE_WEB_HOST",
        "KNOWLEDGE_WEB_PORT",
        "REDIS_PORT",
    )

    env_template = _read(REPO_ROOT / "infra" / "env" / ".env.example")
    for key in (
        "KNOWLEDGE_LOGTO_TAG",
        "KNOWLEDGE_LOGTO_TRUST_PROXY_HEADER",
        "KNOWLEDGE_API_LOG_LEVEL",
        "KNOWLEDGE_API_LOG_FILE_MAX_BYTES",
        "KNOWLEDGE_API_LOG_FILE_BACKUP_COUNT",
        "CLOUDFLARE_TUNNEL_TOKEN",
        "SOURCE_PIPELINE_POLL_INTERVAL_SECONDS",
        "SOURCE_PIPELINE_POLL_BATCH_SIZE",
        "SOURCE_PIPELINE_RECONCILE_INTERVAL_SECONDS",
        "SOURCE_PIPELINE_RECONCILE_BATCH_SIZE",
        "KNOWLEDGE_WEB_COOKIE_SECURE",
        "KNOWLEDGE_WEB_TRUST_PROXY",
        "KNOWLEDGE_WEB_QUOTA_REDIS_PREFIX",
        "KNOWLEDGE_WEB_ANON_BURST_LIMIT",
        "KNOWLEDGE_WEB_ANON_BURST_WINDOW_SECONDS",
        "KNOWLEDGE_WEB_ANON_TOTAL_LIMIT",
        "KNOWLEDGE_WEB_ANON_TOTAL_WINDOW_SECONDS",
        "KNOWLEDGE_WEB_AUTH_BURST_LIMIT",
        "KNOWLEDGE_WEB_AUTH_BURST_WINDOW_SECONDS",
        "KNOWLEDGE_WEB_AUTH_TOTAL_LIMIT",
        "KNOWLEDGE_WEB_AUTH_TOTAL_WINDOW_SECONDS",
        "KNOWLEDGE_WEB_IP_BURST_LIMIT",
        "KNOWLEDGE_WEB_IP_BURST_WINDOW_SECONDS",
        "KNOWLEDGE_WEB_IP_TOTAL_LIMIT",
        "KNOWLEDGE_WEB_IP_TOTAL_WINDOW_SECONDS",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_ANON_BURST_LIMIT",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_ANON_BURST_WINDOW_SECONDS",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_ANON_TOTAL_LIMIT",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_ANON_TOTAL_WINDOW_SECONDS",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_AUTH_BURST_LIMIT",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_AUTH_BURST_WINDOW_SECONDS",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_AUTH_TOTAL_LIMIT",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_AUTH_TOTAL_WINDOW_SECONDS",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_IP_BURST_LIMIT",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_IP_BURST_WINDOW_SECONDS",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_IP_TOTAL_LIMIT",
        "KNOWLEDGE_WEB_TAXONOMY_VIEW_IP_TOTAL_WINDOW_SECONDS",
    ):
        assert f"{key}=" in env_template
    assert "KNOWLEDGE_WEB_QUOTA_ROUTE_OVERRIDES_JSON=" not in env_template
    for key in required_quota_keys:
        assert f"{key}=" in env_template
    for key in removed_quota_keys:
        assert f"{key}=" not in env_template
    for key in removed_topology_keys:
        assert f"{key}=" not in env_template


def test_mcp_startup_script_uses_fixed_container_listener() -> None:
    script = _read(MCP_RUN_SCRIPT)

    assert "KNOWLEDGE_MCP_HOST" not in script
    assert "KNOWLEDGE_MCP_PORT" not in script
    assert "--host 0.0.0.0 --port 8080" in script


def test_taxonomy_view_layout_runtime_startup_script_uses_module_entrypoint() -> None:
    script = _read(TAXONOMY_VIEW_LAYOUT_RUN_SCRIPT)

    assert "python -m entrypoints.taxonomy_view_layout_runtime" in script


def test_taxonomy_layout_precompute_script_uses_operator_module_entrypoint() -> None:
    script = _read(TAXONOMY_LAYOUT_PRECOMPUTE_SCRIPT)

    assert "docker compose" in script
    assert "--environment" in script
    assert "docker-compose.dev.yml" in script
    assert "docker-compose.prod.yml" in script
    assert "docker-compose.taxonomy-layout-precompute.yml" in script
    assert "RUN_ARGS+=(--no-deps)" in script
    assert "ensure_prod_external_volumes" in script
    assert "taxonomy_view_layout_runtime" in script
    assert "$ROOT_DIR/apps/api/src:/app/apps/api/src:ro" in script
    assert "python -m entrypoints.ops.taxonomy_layout_precompute" in script


def test_taxonomy_layout_precompute_compose_sets_four_cpu_default() -> None:
    service = _service_data(TAXONOMY_LAYOUT_PRECOMPUTE_COMPOSE, "taxonomy_view_layout_runtime")

    assert service["cpus"] == "${TAXONOMY_LAYOUT_PRECOMPUTE_CPUS:-4.0}"


def test_dev_and_prod_compose_define_mcp_image_and_ingress_dependencies() -> None:
    dev_mcp = _service_data(DEV_COMPOSE, "mcp")
    prod_mcp = _service_data(PROD_COMPOSE, "mcp")
    prod_nginx = _service_data(PROD_COMPOSE, "nginx")

    assert dev_mcp["image"] == "knowledge-mcp:dev"
    assert dev_mcp["ports"] == ["8002:8080"]
    assert prod_mcp["image"] == "knowledge-mcp:prod"
    assert "mcp" in prod_nginx["depends_on"]
    assert prod_nginx["depends_on"]["web"] == {"condition": "service_healthy"}


def test_prod_nginx_config_is_packaged_in_image_not_bind_mounted() -> None:
    prod_nginx = _service_data(PROD_COMPOSE, "nginx")
    dockerfile = _read(NGINX_DOCKERFILE)

    assert prod_nginx["image"] == "knowledge-nginx:prod"
    assert prod_nginx["build"] == {
        "context": "../..",
        "dockerfile": "infra/docker/nginx/Dockerfile",
    }
    assert "volumes" not in prod_nginx
    assert prod_nginx["healthcheck"]["test"] == ["CMD", "nginx", "-t"]
    assert "FROM nginx:1.29-bookworm" in dockerfile
    assert ("COPY infra/docker/nginx/default.conf /etc/nginx/conf.d/default.conf") in dockerfile


def test_nginx_routes_public_mcp_without_exposing_private_api() -> None:
    nginx = _read(NGINX_CONF)

    assert "set $upstream_mcp mcp:8080;" in nginx
    assert "location /mcp" in nginx
    assert "proxy_pass http://$upstream_mcp;" in nginx
    assert "location /api/v1" not in nginx
