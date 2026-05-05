
from redis.cluster import RedisCluster
import os
import sys

# Redis Config
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "redis123")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
auth_kwargs = {"password": REDIS_PASSWORD} if REDIS_PASSWORD else {}

def clean_redis():
    print(f"Connecting to Redis Cluster at {REDIS_HOST}:{REDIS_PORT}...")
    try:
        r = RedisCluster(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, **auth_kwargs)
        
        # Keys to clean
        keys = [
            "stream:tick:jobs",
            "stream:tick:data",
            "group:mootdx:workers" # Logic key used by some scripts
        ]
        
        print("Cleaning keys:", keys)
        count = r.delete(*keys)
        
        # Verify
        print(f"Deleted {count} keys.")
        print("✅ Redis Clean Complete. Monitoring pending jobs should now be 0.")
        
    except Exception as e:
        print(f"❌ Error Cleaning Redis: {e}")

if __name__ == "__main__":
    confirm = input("⚠️  WARNING: This will DELETE ALL tick jobs and results from Redis. Continue? (y/n): ")
    if confirm.lower() == 'y':
        clean_redis()
    else:
        print("Cancelled.")
