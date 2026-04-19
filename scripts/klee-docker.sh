#!/bin/bash
# KLEE Docker wrapper script
# This script runs KLEE inside the official Docker container

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Run KLEE in Docker with the project mounted
docker run --rm \
    -v "$PROJECT_ROOT:/home/klee/project" \
    -w /home/klee/project \
    klee/klee:3.1 \
    klee "$@"
