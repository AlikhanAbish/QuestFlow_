#!/bin/sh
set -e

echo "Waiting for postgres..."
while ! python -c "
import os, socket, sys
host = os.environ.get('DB_HOST', 'db')
port = int(os.environ.get('DB_PORT', 5432))
try:
    socket.create_connection((host, port), timeout=2).close()
except OSError:
    sys.exit(1)
" 2>/dev/null; do
  sleep 1
done
echo "PostgreSQL started"
