# abstract: Custom PostgreSQL 18 image with extension package baseline for MVP.
# out_of_scope: Database schema migration logic and runtime extension enablement policy.
FROM postgres:18.3-bookworm

ARG PG_EXT_PACKAGES="postgresql-18-pgvector postgresql-contrib-18"

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends $PG_EXT_PACKAGES && \
    rm -rf /var/lib/apt/lists/*

COPY infra/docker/postgres/init/10-roles.sh /docker-entrypoint-initdb.d/10-roles.sh
RUN chmod +x /docker-entrypoint-initdb.d/10-roles.sh
