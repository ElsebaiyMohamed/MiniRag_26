#!/bin/sh
set -e
echo "Runing database Migration"
cd /app/docker/models/db_schemas/minirag26/
alembic upgrade head
cd /app
exec "$@"
