#!/usr/bin/env bash
# abstract: Shared Docker Compose helper for converging online PostgreSQL login roles.
# out_of_scope: Alembic migrations, schema ownership, and non-online PostgreSQL services.

converge_online_postgres_roles() {
  docker compose "$@" up -d --build --wait postgres
  docker compose "$@" exec -T postgres /docker-entrypoint-initdb.d/10-roles.sh
}
