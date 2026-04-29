"""
Abstract: Unit tests enforcing production nginx public surface boundaries.
Out of scope: Runtime container startup and TLS termination behavior.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
NGINX_CONFIG = REPO_ROOT / "infra" / "docker" / "nginx" / "default.conf"


def test_prod_nginx_does_not_expose_private_api_routes() -> None:
    config = NGINX_CONFIG.read_text(encoding="utf-8")

    assert "location /api/" not in config
    assert "proxy_pass http://api:8000" not in config


def test_prod_nginx_routes_web_and_web_api_to_bff() -> None:
    config = NGINX_CONFIG.read_text(encoding="utf-8")

    assert "location /web-api/" in config
    assert "location /" in config
    assert "set $upstream_web web:5173;" in config
    assert config.count("proxy_pass http://$upstream_web;") >= 2


def test_prod_nginx_uses_docker_dns_for_upstream_resolution() -> None:
    config = NGINX_CONFIG.read_text(encoding="utf-8")

    assert "resolver 127.0.0.11 ipv6=off valid=30s;" in config
    assert "resolver_timeout 5s;" in config
    assert "proxy_pass http://web:5173" not in config
    assert "proxy_pass http://logto:" not in config
    assert "proxy_pass http://source_pipeline_webhook_receiver:" not in config
    assert "proxy_pass http://taxonomy_classification_webhook_receiver:" not in config


def test_prod_nginx_routes_source_pipeline_webhook_to_receiver() -> None:
    config = NGINX_CONFIG.read_text(encoding="utf-8")

    assert "location = /source-pipeline/webhooks/job-queue" in config
    assert (
        "set $upstream_source_pipeline_webhook source_pipeline_webhook_receiver:8080;"
    ) in config
    assert "proxy_pass http://$upstream_source_pipeline_webhook;" in config


def test_prod_nginx_routes_taxonomy_classification_webhook_to_receiver() -> None:
    config = NGINX_CONFIG.read_text(encoding="utf-8")

    assert "location = /taxonomy-classification/webhooks/job-queue" in config
    assert (
        "set $upstream_taxonomy_classification_webhook "
        "taxonomy_classification_webhook_receiver:8080;"
    ) in config
    assert "proxy_pass http://$upstream_taxonomy_classification_webhook;" in config


def test_prod_nginx_routes_knowledge_logto_hosts() -> None:
    config = NGINX_CONFIG.read_text(encoding="utf-8")

    assert "server_name knowledge-logto.orbitalis.org;" in config
    assert "set $upstream_logto_auth logto:3001;" in config
    assert "proxy_pass http://$upstream_logto_auth;" in config
    assert "server_name admin.knowledge-logto.internal.home.arpa;" in config
    assert "set $upstream_logto_admin logto:3002;" in config
    assert "proxy_pass http://$upstream_logto_admin;" in config
