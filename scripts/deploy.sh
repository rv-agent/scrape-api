#!/bin/bash
# ScrapeAPI Deployment Script
set -e

ACTION="${1:-help}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

case "$ACTION" in
    start)
        echo "▶ Starting ScrapeAPI..."
        cd "$PROJECT_DIR/docker"
        docker-compose up -d
        echo "✓ Services started"
        docker-compose ps
        ;;
    stop)
        echo "▶ Stopping ScrapeAPI..."
        cd "$PROJECT_DIR/docker"
        docker-compose down
        echo "✓ Services stopped"
        ;;
    restart)
        echo "▶ Restarting ScrapeAPI..."
        cd "$PROJECT_DIR/docker"
        docker-compose restart
        echo "✓ Services restarted"
        ;;
    logs)
        cd "$PROJECT_DIR/docker"
        docker-compose logs -f --tail=100
        ;;
    status)
        cd "$PROJECT_DIR/docker"
        docker-compose ps
        echo ""
        echo "▶ Health check..."
        curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "API not running"
        ;;
    deploy)
        echo "▶ Full deploy (build + restart)..."
        cd "$PROJECT_DIR/docker"
        docker-compose build --no-cache
        docker-compose up -d
        echo "✓ Deployed"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|status|deploy}"
        exit 1
        ;;
esac
