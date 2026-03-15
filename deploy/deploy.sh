#!/bin/bash
set -e

PROJECT_DIR="/opt/aizavod"
VENV="$PROJECT_DIR/.venv"

echo "=== AIZAVOD Deploy ==="

cd "$PROJECT_DIR"

# Pull latest code
git checkout -- aizavod.db 2>/dev/null || true
git pull origin main

# Install Python dependencies
$VENV/bin/pip install -r requirements.txt -q

# Build web-ui (if node_modules exist)
if [ -d "web-ui/node_modules" ]; then
    echo "Building web-ui..."
    cd web-ui && npm run build && cd ..
fi

# Ensure media directories exist
mkdir -p media/reference media/generated media/processed

# Restart service
systemctl restart aizavod

echo "=== Deploy complete ==="
systemctl status aizavod --no-pager
