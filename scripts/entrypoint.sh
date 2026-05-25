#!/bin/sh
set -e

/app/scripts/wait_for_db.sh

echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "Redis started"

exec "$@"
