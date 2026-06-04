#!/bin/bash
# ScrapeAPI CI/CD Pipeline
# Runs: lint → test → build → deploy
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$PROJECT_DIR/.venv"
PYTHON="${PYTHON:-python3}"

echo "═══════════════════════════════════════"
echo "  ScrapeAPI CI/CD Pipeline"
echo "═══════════════════════════════════════"

# Step 1: Lint
echo ""
echo "▶ Step 1: Linting..."
cd "$PROJECT_DIR"
if command -v ruff &> /dev/null; then
    ruff check src/ --select E,F,W --ignore E501
    echo "✓ Lint passed"
else
    echo "⚠ ruff not found, skipping lint"
fi

# Step 2: Tests
echo ""
echo "▶ Step 2: Running tests..."
$PYTHON -m pytest tests/ -v --tb=short -x 2>&1 | tail -20
echo "✓ Tests completed"

# Step 3: Build Docker image
echo ""
echo "▶ Step 3: Building Docker image..."
if command -v docker &> /dev/null; then
    docker build -t scrapeapi:latest -f docker/Dockerfile "$PROJECT_DIR"
    echo "✓ Docker image built: scrapeapi:latest"
else
    echo "⚠ Docker not found, skipping build"
fi

# Step 4: Deploy (if DEPLOY_TARGET set)
echo ""
if [ -n "$DEPLOY_TARGET" ]; then
    echo "▶ Step 4: Deploying to $DEPLOY_TARGET..."
    case "$DEPLOY_TARGET" in
        docker-compose)
            cd "$PROJECT_DIR/docker"
            docker-compose up -d
            echo "✓ Deployed via docker-compose"
            ;;
        render)
            echo "⚠ Render deploy requires manual trigger or API key"
            ;;
        *)
            echo "⚠ Unknown deploy target: $DEPLOY_TARGET"
            ;;
    esac
else
    echo "▶ Step 4: Deploy skipped (set DEPLOY_TARGET=docker-compose to enable)"
fi

echo ""
echo "═══════════════════════════════════════"
echo "  Pipeline Complete"
echo "═══════════════════════════════════════"
