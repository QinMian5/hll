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
