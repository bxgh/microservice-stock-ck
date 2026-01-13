#!/bin/bash
# =================================================================
# Remote Node Deployment Script for Sharded Tick Data Acquisition
# =================================================================
# Usage: Run this script on Server 58 and Server 111
#
# Prerequisite:
#   Ensure you are in the project root directory
#   Ensure 'git pull' works (credentials configured)
# =================================================================

set -e

echo "🚀 Starting Deployment on $(hostname -I | awk '{print $1}')..."

# 1. Pull Latest Code
echo "📥 Pulling latest code..."
git pull origin feature/quant-strategy

# 2. Update Environment Variables
echo "⚙️  Updating .env configuration..."
if ! grep -q "REDIS_HOST" .env; then
    echo "REDIS_HOST=192.168.151.41" >> .env
    echo "REDIS_PORT=6379" >> .env
    echo "REDIS_PASSWORD=redis123" >> .env
    echo "REDIS_CLUSTER=false" >> .env
    echo "✅ Added Redis Standalone config to .env"
else
    echo "ℹ️  Redis config already exists in .env"
fi

# 3. Rebuild Docker Images
echo "🐳 Rebuilding gsd-worker image..."
docker build -t gsd-worker -f services/gsd-worker/Dockerfile . \
  --build-arg ENABLE_PROXY=true \
  --build-arg PROXY_URL=http://192.168.151.18:3128

echo "🐳 Rebuilding mootdx-api image..."
docker build -t microservice-stock-mootdx-api -f services/mootdx-api/Dockerfile . \
  --build-arg ENABLE_PROXY=true \
  --build-arg PROXY_URL=http://192.168.151.18:3128

# 4. Restart Services
echo "🔄 Restarting mootdx-api..."
docker compose -f docker-compose.microservices.yml up -d --force-recreate mootdx-api

# 4.1 Health Check for mootdx-api
echo "🔍 Checking mootdx-api health..."
MAX_RETRIES=10
RETRY_COUNT=0
HEALTH_URL="http://localhost:8003/health"

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s $HEALTH_URL | grep -q '"status":"healthy"'; then
        echo "✅ mootdx-api is healthy!"
        break
    else
        echo "⏳ Waiting for mootdx-api to become healthy... ($((RETRY_COUNT+1))/$MAX_RETRIES)"
        RETRY_COUNT=$((RETRY_COUNT+1))
        sleep 3
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ mootdx-api health check failed!"
    exit 1
fi

# 5. Configure Distributed Scheduling (Cron)
echo "⏰ Configuring Distributed Scheduling..."
SERVER_IP=$(hostname -I | awk '{print $1}')
CRON_SCHEDULE="35 16 * * 1-5" # 16:35 on trading days

if [[ "$SERVER_IP" == "192.168.151.41" ]]; then
    SHARD_INDEX=0
    echo "📍 Detected Server 41 -> Assigning Shard 0"
elif [[ "$SERVER_IP" == "192.168.151.58" ]]; then
    SHARD_INDEX=1
    echo "📍 Detected Server 58 -> Assigning Shard 1"
elif [[ "$SERVER_IP" == "192.168.151.111" ]]; then
    SHARD_INDEX=2
    echo "📍 Detected Server 111 -> Assigning Shard 2"
else
    echo "⚠️  Unknown Server IP ($SERVER_IP). Skipping Cron setup."
    exit 0
fi

# Ensure persistent data directory exists
mkdir -p /home/bxgh/microservice-stock/data/gsd-worker

# Define the docker command for this shard (with persistence)
JOB_CMD="docker run -d --rm --network host --env-file /root/microservice-stock/.env -v /home/bxgh/microservice-stock/data/gsd-worker:/app/data -v /home/bxgh/microservice-stock/libs/gsd-shared:/app/libs/gsd-shared:ro gsd-worker jobs.sync_tick --mode incremental --scope all --shard-index $SHARD_INDEX --shard-total 3"

# Update Crontab (Idempotent)
# Remove existing entry for sync_tick to avoid duplicates
(crontab -l 2>/dev/null | grep -v "src.jobs.sync_tick") | crontab -

# Add new entry
(crontab -l 2>/dev/null; echo "$CRON_SCHEDULE $JOB_CMD >> /var/log/gsd-tick-shard-$SHARD_INDEX.log 2>&1") | crontab -

echo "✅ Cron task configured for Shard $SHARD_INDEX"
echo "   Schedule: $CRON_SCHEDULE"
echo "   Log: /var/log/gsd-tick-shard-$SHARD_INDEX.log"

echo "✅ Deployment Complete on $SERVER_IP!"
echo "   Next Step: Check logs with 'docker logs -f microservice-stock-mootdx-api'"
