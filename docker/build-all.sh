#!/usr/bin/env bash
#
# docker/build-all.sh - build all ClassroomEnv Docker images in the
# correct order. classroomenv:core MUST be built first since every
# other profile image is FROM classroomenv:core.
#
# Usage (run from the repo root, not from inside docker/):
#   ./docker/build-all.sh
#   ./docker/build-all.sh web ad        # build only specific profiles
#                                          (core is always built first)
#
# Each image is tagged classroomenv:<profile>.

set -euo pipefail

cd "$(dirname "$0")/.."   # repo root, so COPY classroomenv.py finds the file

PROFILES=(web osint ad wireless exploitation extras full)

if [ "$#" -gt 0 ]; then
    PROFILES=("$@")
fi

echo "==> Building base image: classroomenv:core"
docker build -f docker/Dockerfile.core -t classroomenv:core .

for p in "${PROFILES[@]}"; do
    if [ "$p" = "core" ]; then
        continue
    fi
    echo "==> Building classroomenv:$p"
    docker build -f "docker/Dockerfile.$p" -t "classroomenv:$p" .
done

echo "==> Done. Images:"
docker images "classroomenv:*"
