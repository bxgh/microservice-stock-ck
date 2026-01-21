import mmh3
import os

def get_shard(code, total=3):
    # 模仿系统的分片逻辑 (xxhash64 or mmh3? 之前的文档说是 xxHash64)
    # 注意：我们这里使用 redis smembers 结果来对照
    return

import redis
r = redis.Redis(host='127.0.0.1', port=6379, password='redis123', decode_responses=True)

for i in range(3):
    count = r.scard(f"metadata:stock_codes:shard:{i}")
    print(f"Shard {i} has {count} stocks")

# 检查前10个
shard0 = list(r.smembers("metadata:stock_codes:shard:0"))[:5]
shard1 = list(r.smembers("metadata:stock_codes:shard:1"))[:5]
shard2 = list(r.smembers("metadata:stock_codes:shard:2"))[:5]

print(f"Sample Shard 0: {shard0}")
print(f"Sample Shard 1: {shard1}")
print(f"Sample Shard 2: {shard2}")
