#!/bin/bash

# ==============================================================================
# Docker Image Cleanup Script
# ==============================================================================
# 
# Usage: ./cleanup_docker.sh [--dry-run]
# 
# Description:
#   Identifies and effectively removes unused Docker images, while strictly 
#   conserving images defined in the RETENTION_LIST.
#
# ==============================================================================

RETENTION_LIST=(
    # --- Infrastructure Databases & Message Queues ---
    "nacos/nacos-server:v2.2.3"
    "redis:7.2.4-alpine"
    "redis:7.0-alpine"
    "clickhouse/clickhouse-server:latest"
    "rabbitmq:3.12-management-alpine"
    "mysql:8.0"

    # --- Monitoring & Logging ---
    "prom/prometheus:latest"
    "grafana/grafana:latest"
    "consul:1.16"
    "nginx:alpine"

    # --- Base Images ---
    "python:3.12-slim"

    # --- Core Application Services (Latest) ---
    "gsd-worker:latest"
    "task-orchestrator:latest"
    "gsd-api:latest"
    "get-stockdata:latest"
    
    # --- Other Active Services ---
    "quant-strategy:dev"
    "microservice-stock-mootdx-api:latest"
    "microservice-stock-mootdx-source:latest"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
fi

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}       Docker Image Cleanup Utility       ${NC}"
echo -e "${BLUE}======================================================${NC}"
echo

if $DRY_RUN; then
    echo -e "${YELLOW}[MODE] Dry Run - No images will be deleted.${NC}\n"
else
    echo -e "${RED}[MODE] Active - Images WILL be deleted.${NC}\n"
fi

# 1. Prune Dangling Images First
echo -e "${BLUE}>>> Step 1: Pruning dangling (un-tagged) intermediate images...${NC}"
if $DRY_RUN; then
    echo "docker image prune -f (Skipped in dry-run)"
else
    docker image prune -f
fi
echo

# 2. Get All Local Images
echo -e "${BLUE}>>> Step 2: Analyzing named images...${NC}"

# Get list of "Repository:Tag"
ALL_IMAGES=$(docker images --format "{{.Repository}}:{{.Tag}}")

# Get list of images used by currently running containers (Ancestor)
USED_IMAGES=$(docker ps --format "{{.Image}}")

for IMG in $ALL_IMAGES; do
    # Skip <none> if prune missed them or if they show up differently
    if [[ "$IMG" == "<none>:<none>" ]]; then
        continue
    fi

    KEEP=false
    REASON=""

    # A. Check against Retention List
    for PATTERN in "${RETENTION_LIST[@]}"; do
        if [[ "$IMG" == "$PATTERN" ]]; then
            KEEP=true
            REASON="In Retention List"
            break
        fi
    done

    # B. Check against Running Containers
    if [ "$KEEP" = false ]; then
        # Check if this image is an ancestor of any running container
        # Note: 'docker ps' gives image names. 
        # For precision, strictly we might check image ID, but name check is usually enough for cleanup.
        for USED in $USED_IMAGES; do
            if [[ "$IMG" == "$USED" ]]; then
                KEEP=true
                REASON="Currently Running"
                break
            fi
        done
    fi

    # C. Strategy Decision
    if [ "$KEEP" = true ]; then
        echo -e "${GREEN}[KEEP]${NC} $IMG ($REASON)"
    else
        echo -e "${RED}[DELETE]${NC} $IMG"
        if ! $DRY_RUN; then
            docker rmi "$IMG" || true
        fi
    fi
done

echo
echo -e "${BLUE}>>> Cleanup Complete.${NC}"
