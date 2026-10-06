#!/bin/bash

# AI-Interview production deployment helper
# CI/CD is the preferred path; this script is for explicit manual SHA deploys.

set -Eeuo pipefail

# Configuration
COMPOSE_FILES="${COMPOSE_FILES:-"-f docker-compose.yml"}"
API_PORT="${API_PORT:-8006}"
TIMEOUT="${TIMEOUT:-180}"
BACKEND_IMAGE="${BACKEND_IMAGE:-}"

if [[ -z "$BACKEND_IMAGE" ]]; then
    echo "❌ BACKEND_IMAGE is required and must be an immutable ACR SHA image."
    echo "   Example: BACKEND_IMAGE=<ACR仓库>:<commit-sha> bash scripts/deploy.sh"
    exit 1
fi

export BACKEND_IMAGE

echo "🚀 Starting AI-Interview deployment..."

echo "📋 Using compose files: $COMPOSE_FILES"
echo "🐳 Using Docker image: $BACKEND_IMAGE"
echo "🔌 Using API port: $API_PORT"
echo "🏥 Health endpoint: http://app:${API_PORT}/api/v1/config/health"

# Function to check application health
check_health() {
    local timeout=$1
    echo "⏳ Waiting for application to be ready..."

    while [ $timeout -gt 0 ]; do
        if docker exec ai-interview-app python -c "import urllib.request; urllib.request.urlopen('http://localhost:${API_PORT}/api/v1/config/health', timeout=5)" >/dev/null 2>&1; then
            echo "✅ Application is ready!"
            return 0
        fi
        echo "Waiting... ($timeout seconds left)"
        sleep 5
        timeout=$((timeout - 5))
    done

    echo "❌ Application failed to start within timeout"
    return 1
}

# Function to show service logs on failure
show_logs() {
    echo "📋 Service logs:"
    docker compose $COMPOSE_FILES logs --tail=50
}

# Main deployment process
main() {
    echo "🔍 Environment check:"
    echo "  - API_PORT: $API_PORT"
    echo "  - BACKEND_IMAGE: $BACKEND_IMAGE"
    echo "  - COMPOSE_FILES: $COMPOSE_FILES"
    echo "  - HEALTH_ENDPOINT: $HEALTH_ENDPOINT"

    echo "📥 Pulling immutable backend image..."
    docker compose $COMPOSE_FILES pull app celery-worker celery-beat

    echo "🏃 Starting PostgreSQL and Redis..."
    docker compose $COMPOSE_FILES up -d postgres redis

    echo "🏃 Updating app without tearing down the stack..."
    docker compose $COMPOSE_FILES up -d --force-recreate --no-deps app

    if ! check_health $TIMEOUT; then
        show_logs
        exit 1
    fi

    echo "🗄️ Running database migrations..."
    docker compose $COMPOSE_FILES exec -T app alembic upgrade head

    echo "🏃 Updating Celery services..."
    docker compose $COMPOSE_FILES up -d --force-recreate --no-deps celery-worker celery-beat

    echo "🏃 Rebuilding and reloading Nginx..."
    docker compose $COMPOSE_FILES build --no-cache nginx
    docker compose $COMPOSE_FILES up -d --force-recreate --no-deps nginx

    # Show running containers and their ports
    echo "📊 Container status:"
    docker compose $COMPOSE_FILES ps
    echo "🔌 Port mapping:"
    docker ps --format "table {{.Names}}\t{{.Ports}}"

    # Show service status
    echo "📊 Service status:"
    docker compose $COMPOSE_FILES ps

    # Final health check
    echo "🏥 Final health check..."
    if check_health 30; then
        echo "✅ Deployment completed successfully!"
        echo "🔗 Application is healthy inside ai-interview-app:${API_PORT}"
    else
        echo "⚠️ Health check failed after deployment"
        show_logs
        exit 1
    fi
}

# Error handling
trap 'echo "❌ Deployment failed. Check logs above."; show_logs; exit 1' ERR

# Run main deployment
main "$@"
