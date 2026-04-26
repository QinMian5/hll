"""
Abstract: Unit tests enforcing production nginx API proxy path preservation.
Out of scope: Runtime container startup and TLS termination behavior.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
NGINX_CONFIG = REPO_ROOT / "infra" / "docker" / "nginx" / "default.conf"


def test_prod_nginx_preserves_api_prefix_for_contract_paths() -> None:
    config = NGINX_CONFIG.read_text(encoding="utf-8")

    assert "location /api/" in config
    assert "proxy_pass http://api:8000;" in config
    assert "proxy_pass http://api:8000/;" not in config


def test_prod_nginx_routes_source_pipeline_webhook_to_receiver() -> None:
    config = NGINX_CONFIG.read_text(encoding="utf-8")

    assert "location = /source-pipeline/webhooks/job-queue" in config
    assert "proxy_pass http://source_pipeline_webhook_receiver:8080;" in config


def test_prod_nginx_routes_taxonomy_classification_webhook_to_receiver() -> None:
    config = NGINX_CONFIG.read_text(encoding="utf-8")

    assert "location = /taxonomy-classification/webhooks/job-queue" in config
    assert "proxy_pass http://taxonomy_classification_webhook_receiver:8080;" in config


def test_prod_nginx_routes_knowledge_logto_hosts() -> None:
    config = NGINX_CONFIG.read_text(encoding="utf-8")

    assert "server_name knowledge-logto.orbitalis.org;" in config
    assert "proxy_pass http://logto:3001/;" in config
    assert "server_name admin.knowledge-logto.internal.home.arpa;" in config
    assert "proxy_pass http://logto:3002/;" in config
