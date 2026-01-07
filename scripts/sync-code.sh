#!/bin/bash
# Sync code from .58 to .41
# Usage: ./sync-code.sh

SOURCE_DIR="/home/bxgh/microservice-stock"
TARGET_HOST="192.168.151.41"
TARGET_DIR="/home/bxgh/microservice-stock"

echo "Starting sync to $TARGET_HOST..."

# Exclude data, logs, venv, and .git (to keep the target's git state or just sync pure code)
# Note: If .git is excluded, .41 won't be a git repo unless initialized.
# Usually, syncing .git is better if .41 is a mirror/backup.
# But for now, we follow the plan to exclude it to avoid conflicts.

rsync -avz --delete \
    --exclude='.git' \
    --exclude='data' \
    --exclude='logs' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    $SOURCE_DIR/ bxgh@$TARGET_HOST:$TARGET_DIR/

echo "Sync completed at $(date)"
