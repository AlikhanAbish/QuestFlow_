#!/bin/sh
set -e

echo "Waiting for postgres..."
while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
  sleep 1
done
echo "PostgreSQL started"
