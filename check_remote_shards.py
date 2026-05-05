import redis

def check():
    r = redis.Redis(host='127.0.0.1', port=6379, password='redis123', decode_responses=True)
    codes_to_check = ['300499', '300516', '300510', '600519', '000001']
    
    for code in codes_to_check:
        found_in = []
        for i in range(3):
            shard_key = f"metadata:stock_codes:shard:{i}"
            # 注意：Redis 存的可能是 000001.SZ 格式，也可能是 sz000001 格式
            # 我们先尝试子串匹配
            members = r.smembers(shard_key)
            if any(code in m for m in members):
                found_in.append(i)
        print(f"Code {code} found in Shards: {found_in}")

if __name__ == "__main__":
    check()
