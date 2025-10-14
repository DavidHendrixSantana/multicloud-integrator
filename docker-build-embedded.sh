#!/bin/bash
# Build script for embedded Docker setup

set -e

echo "Building Multi-Cloud Integrator with embedded configuration..."

# Backup original .dockerignore if exists
if [ -f .dockerignore ]; then
    cp .dockerignore .dockerignore.backup
fi

# Use the embedded dockerignore
cp .dockerignore.embedded .dockerignore

# Build the image
docker-compose -f docker-compose.embedded.yml build --no-cache

# Restore original .dockerignore
if [ -f .dockerignore.backup ]; then
    mv .dockerignore.backup .dockerignore
else
    rm .dockerignore 2>/dev/null || true
fi

echo "✅ Embedded Docker image built successfully!"
echo ""
echo "Usage examples:"
echo "  # Run with embedded configuration:"
echo "  docker-compose -f docker-compose.embedded.yml run --rm multicloud-integrator"
echo ""
echo "  # Check configuration:"
echo "  docker-compose -f docker-compose.embedded.yml run --rm multicloud-integrator python main.py config-check"
echo ""
echo "  # List providers:"
echo "  docker-compose -f docker-compose.embedded.yml run --rm multicloud-integrator python main.py providers"