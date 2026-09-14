#!/bin/sh
# Runs once, on first boot of an empty pgdata volume (docker-entrypoint-initdb.d).
# Recreates what lab 11 set up by hand: the role db_replica's pg_basebackup
# connects as, and the pg_hba rule that allows replication connections.
set -e

psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -c "CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'replicate';"

echo 'host replication replicator all scram-sha-256' >> "$PGDATA/pg_hba.conf"
