#!/bin/sh
set -eu
# Coolify helper containers need their own buildx metadata, not a new daemon.
if ! docker buildx inspect lobby-firecrawl-builder >/dev/null 2>&1; then
  docker buildx create --name lobby-firecrawl-builder --driver docker-container \
    --driver-opt memory=4g,memory-swap=4g,cpu-period=100000,cpu-quota=200000 >/dev/null
fi
docker buildx bake --builder lobby-firecrawl-builder -f docker-compose.build.yml --load
