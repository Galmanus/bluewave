#!/bin/bash
set -e

echo "Bluewave Backend — Starting up..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
MAX_RETRIES=30
RETRY=0
until pg_isready -h postgres -U "${POSTGRES_USER:-bluewave}" -d "${POSTGRES_DB:-bluewave}" -q 2>/dev/null; do
    RETRY=$((RETRY + 1))
    if [ "$RETRY" -ge "$MAX_RETRIES" ]; then
        echo "ERROR: PostgreSQL not ready after ${MAX_RETRIES} attempts. Exiting."
        exit 1
    fi
    echo "  PostgreSQL not ready yet (attempt $RETRY/$MAX_RETRIES)..."
    sleep 1
done
echo "PostgreSQL is ready."

# Run database migrations
echo "Running Alembic migrations..."
alembic upgrade head
echo "Migrations complete."

# Start the application
echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
