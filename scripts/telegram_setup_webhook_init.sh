#!/bin/sh
# telegram_setup_webhook_init.sh
# One-time webhook registration during app startup
# Runs once, then exits (used in docker-compose as a one-time service)

set -e

# Wait for database
echo "⏳ Waiting for database..."
/app/scripts/wait_for_db.sh

# Setup webhook
echo "🔗 Setting up Telegram webhook..."
python manage.py telegram_setup_webhook

# Exit successfully
echo "✅ Webhook initialized"
exit 0
