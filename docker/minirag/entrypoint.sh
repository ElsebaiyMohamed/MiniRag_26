#!/bin/sh
set -e
echo "Runing database Migration"
cd /app/docker/models/db_schemas/minirag26/
alembic upgrade head
cd /app

# Ensure multiprocess directory for prometheus exists and is clean
if [ -n "$PROMETHEUS_MULTIPROC_DIR" ]; then
    mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
    rm -rf "${PROMETHEUS_MULTIPROC_DIR:?}"/*
fi

exec "$@"
