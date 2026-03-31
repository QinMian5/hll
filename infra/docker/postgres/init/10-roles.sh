#!/usr/bin/env bash
# abstract: Initialize application and migration roles for the knowledge database.
# out_of_scope: Backup setup, replication, and non-role PostgreSQL hardening.
set -euo pipefail

db_name="${POSTGRES_DB:?POSTGRES_DB is required}"
app_user="${APP_DB_USER:?APP_DB_USER is required}"
app_password="${APP_DB_PASSWORD:?APP_DB_PASSWORD is required}"
migration_user="${MIGRATION_DB_USER:?MIGRATION_DB_USER is required}"
migration_password="${MIGRATION_DB_PASSWORD:?MIGRATION_DB_PASSWORD is required}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db_name" <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${app_user}') THEN
    CREATE ROLE "${app_user}" LOGIN PASSWORD '${app_password}';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${migration_user}') THEN
    CREATE ROLE "${migration_user}" LOGIN PASSWORD '${migration_password}';
  END IF;
END
\$\$;

GRANT CONNECT ON DATABASE "${db_name}" TO "${app_user}";
GRANT CONNECT ON DATABASE "${db_name}" TO "${migration_user}";

GRANT USAGE ON SCHEMA public TO "${app_user}";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "${app_user}";
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO "${app_user}";

GRANT USAGE, CREATE ON SCHEMA public TO "${migration_user}";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "${migration_user}";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "${migration_user}";

ALTER DEFAULT PRIVILEGES FOR ROLE "${migration_user}" IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "${app_user}";
ALTER DEFAULT PRIVILEGES FOR ROLE "${migration_user}" IN SCHEMA public
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO "${app_user}";

-- pgvector extension creation typically requires elevated rights.
ALTER ROLE "${migration_user}" WITH SUPERUSER;
SQL

