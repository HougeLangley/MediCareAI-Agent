#!/usr/bin/env bash
# ==========================================
# Production Deployment Script
# Run this on the VPS after git pull
# ==========================================

set -euo pipefail

echo "🔄 MediCareAI-Agent Production Deploy"
echo "===================================="

# Pull latest code
git pull origin main

# Validate env file exists
if [[ ! -f .env ]]; then
    echo "❌ .env not found! Copy from .env.example and configure."
    exit 1
fi

# Build & restart
docker compose -f docker-compose.yml down
docker compose -f docker-compose.yml build --no-cache
docker compose -f docker-compose.yml up -d

# Health check
echo "🔍 Running health check..."
sleep 5
if curl -sf http://localhost:8000/health > /dev/null; then
    echo "✅ Deployment successful!"
else
    echo "❌ Health check failed. Check logs: docker compose logs backend"
    exit 1
fi
