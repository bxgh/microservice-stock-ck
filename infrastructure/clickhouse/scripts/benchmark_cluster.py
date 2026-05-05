#!/usr/bin/env python3
"""
ClickHouse 3-Shard 集群性能基准测试

测试场景：
1. 写入性能：批量插入 10,000 条 tick 数据
2. 单股查询：查询单只股票的数据
3. 全市场扫描：聚合查询所有股票
4. 分片分布：验证数据均匀分布
"""

import time
import random
from datetime import datetime, timedelta
from clickhouse_driver import Client

# 配置
CLICKHOUSE_HOST = '192.168.151.41'
CLICKHOUSE_USER = 'admin'
CLICKHOUSE_PASSWORD = 'admin123'
CLICKHOUSE_DB = 'stock_data'

# 测试参数
NUM_STOCKS = 100  # 测试股票数量
NUM_TICKS_PER_STOCK = 100  # 每只股票的 tick 数量
TOTAL_RECORDS = NUM_STOCKS * NUM_TICKS_PER_STOCK

def connect():
    """连接 ClickHouse"""
    return Client(
        host=CLICKHOUSE_HOST,
        user=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD,
        database=CLICKHOUSE_DB
    )

def generate_test_data():
    """生成测试数据"""
    print(f"生成 {TOTAL_RECORDS:,} 条测试数据...")
    
    data = []
    base_time = datetime.now().replace(hour=9, minute=30, second=0, microsecond=0)
    
    for stock_idx in range(NUM_STOCKS):
        stock_code = f"{stock_idx:06d}"
        base_price = random.uniform(10, 500)
        
        for tick_idx in range(NUM_TICKS_PER_STOCK):
            tick_time = base_time + timedelta(seconds=tick_idx * 3)
            price = base_price * (1 + random.uniform(-0.01, 0.01))
            volume = random.randint(100, 10000)
            amount = price * volume
            direction = random.randint(0, 2)
            
            data.append((
                stock_code,
                tick_time.date(),
                tick_time.strftime('%H:%M:%S'),
                round(price, 3),
                volume,
                round(amount, 2),
                direction,
                datetime.now()
            ))
    
    return data

def test_write_performance(client, data):
    """测试写入性能"""
    print(f"\n{'='*60}")
    print("测试 1: 批量写入性能")
    print(f"{'='*60}")
    
    # 清空测试表
    print("清空现有测试数据...")
    client.execute("TRUNCATE TABLE tick_data_local ON CLUSTER stock_cluster")
    time.sleep(2)
    
    # 批量写入
    print(f"写入 {len(data):,} 条记录...")
    start_time = time.time()
    
    client.execute(
        "INSERT INTO tick_data VALUES",
        data,
        types_check=True
    )
    
    elapsed = time.time() - start_time
    throughput = len(data) / elapsed
    
    print(f"✓ 写入完成")
    print(f"  耗时: {elapsed:.2f} 秒")
    print(f"  吞吐量: {throughput:,.0f} 条/秒")
    print(f"  平均延迟: {elapsed/len(data)*1000:.2f} ms/条")
    
    return elapsed, throughput

def test_single_stock_query(client):
    """测试单股查询性能"""
    print(f"\n{'='*60}")
    print("测试 2: 单股查询性能")
    print(f"{'='*60}")
    
    test_stock = "000050"
    
    start_time = time.time()
    result = client.execute(f"""
        SELECT 
            stock_code,
            count() AS tick_count,
            min(price) AS low,
            max(price) AS high,
            avg(price) AS avg_price
        FROM tick_data
        WHERE stock_code = '{test_stock}'
        GROUP BY stock_code
    """)
    elapsed = time.time() - start_time
    
    print(f"✓ 查询完成")
    print(f"  股票代码: {test_stock}")
    print(f"  查询耗时: {elapsed*1000:.2f} ms")
    if result:
        print(f"  返回记录: {result[0][1]} 条")
        print(f"  价格范围: {result[0][2]:.2f} ~ {result[0][3]:.2f}")
    
    return elapsed

def test_full_scan_query(client):
    """测试全市场扫描性能"""
    print(f"\n{'='*60}")
    print("测试 3: 全市场聚合查询")
    print(f"{'='*60}")
    
    start_time = time.time()
    result = client.execute("""
        SELECT 
            count() AS total_ticks,
            count(DISTINCT stock_code) AS stock_count,
            sum(volume) AS total_volume,
            sum(amount) AS total_amount
        FROM tick_data
    """)
    elapsed = time.time() - start_time
    
    print(f"✓ 查询完成")
    print(f"  查询耗时: {elapsed*1000:.2f} ms")
    if result:
        print(f"  总 Tick 数: {result[0][0]:,}")
        print(f"  股票数量: {result[0][1]}")
        print(f"  总成交量: {result[0][2]:,}")
        print(f"  总成交额: {result[0][3]:,.2f}")
    
    return elapsed

def test_shard_distribution(client):
    """测试数据分片分布"""
    print(f"\n{'='*60}")
    print("测试 4: 数据分片分布")
    print(f"{'='*60}")
    
    # 查询每个分片的数据量
    import subprocess
    
    shards = {
        'Server 41': '192.168.151.41',
        'Server 58': '192.168.151.58',
        'Server 111': '192.168.151.111'
    }
    
    distribution = {}
    for name, ip in shards.items():
        cmd = f"""ssh bxgh@{ip} "docker exec microservice-stock-clickhouse clickhouse-client --user admin --password admin123 -q 'SELECT count() FROM stock_data.tick_data_local'" 2>/dev/null"""
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        count = int(result.stdout.strip()) if result.stdout.strip() else 0
        distribution[name] = count
    
    total = sum(distribution.values())
    
    print(f"✓ 分片分布:")
    for name, count in distribution.items():
        percentage = (count / total * 100) if total > 0 else 0
        print(f"  {name}: {count:,} 条 ({percentage:.1f}%)")
    
    # 计算分布均衡度（标准差）
    import statistics
    if len(distribution) > 1:
        std_dev = statistics.stdev(distribution.values())
        mean = statistics.mean(distribution.values())
        cv = (std_dev / mean * 100) if mean > 0 else 0
        print(f"\n  均衡度: {cv:.1f}% (变异系数，越小越均衡)")
    
    return distribution

def test_parallel_query_speedup(client):
    """测试并行查询加速比"""
    print(f"\n{'='*60}")
    print("测试 5: 并行查询加速比")
    print(f"{'='*60}")
    
    # 查询 10 只股票的聚合数据
    stock_list = [f"{i:06d}" for i in range(0, 50, 5)]
    
    start_time = time.time()
    result = client.execute(f"""
        SELECT 
            stock_code,
            count() AS tick_count,
            avg(price) AS avg_price
        FROM tick_data
        WHERE stock_code IN ({','.join(f"'{s}'" for s in stock_list)})
        GROUP BY stock_code
        ORDER BY stock_code
    """)
    elapsed = time.time() - start_time
    
    print(f"✓ 并行查询完成")
    print(f"  查询股票数: {len(stock_list)}")
    print(f"  查询耗时: {elapsed*1000:.2f} ms")
    print(f"  平均每股: {elapsed/len(stock_list)*1000:.2f} ms")
    
    return elapsed

def main():
    """主测试流程"""
    print("="*60)
    print("ClickHouse 3-Shard 集群性能基准测试")
    print("="*60)
    print(f"集群配置: {CLICKHOUSE_HOST}")
    print(f"测试规模: {NUM_STOCKS} 只股票 × {NUM_TICKS_PER_STOCK} ticks = {TOTAL_RECORDS:,} 条")
    print()
    
    # 连接
    print("连接 ClickHouse...")
    client = connect()
    print("✓ 连接成功")
    
    # 生成测试数据
    data = generate_test_data()
    
    # 执行测试
    results = {}
    
    # 1. 写入性能
    write_time, write_throughput = test_write_performance(client, data)
    results['write_time'] = write_time
    results['write_throughput'] = write_throughput
    
    # 等待数据落盘
    time.sleep(3)
    
    # 2. 单股查询
    results['single_query_time'] = test_single_stock_query(client)
    
    # 3. 全市场扫描
    results['full_scan_time'] = test_full_scan_query(client)
    
    # 4. 分片分布
    results['distribution'] = test_shard_distribution(client)
    
    # 5. 并行查询
    results['parallel_query_time'] = test_parallel_query_speedup(client)
    
    # 总结
    print(f"\n{'='*60}")
    print("测试总结")
    print(f"{'='*60}")
    print(f"✓ 写入吞吐量: {results['write_throughput']:,.0f} 条/秒")
    print(f"✓ 单股查询延迟: {results['single_query_time']*1000:.2f} ms")
    print(f"✓ 全市场扫描: {results['full_scan_time']*1000:.2f} ms")
    print(f"✓ 并行查询: {results['parallel_query_time']*1000:.2f} ms")
    
    # 评估
    print(f"\n{'='*60}")
    print("性能评估")
    print(f"{'='*60}")
    
    if results['write_throughput'] > 10000:
        print("✓ 写入性能: 优秀 (>10k 条/秒)")
    elif results['write_throughput'] > 5000:
        print("✓ 写入性能: 良好 (>5k 条/秒)")
    else:
        print("⚠ 写入性能: 需优化 (<5k 条/秒)")
    
    if results['single_query_time'] < 0.05:
        print("✓ 查询性能: 优秀 (<50ms)")
    elif results['single_query_time'] < 0.1:
        print("✓ 查询性能: 良好 (<100ms)")
    else:
        print("⚠ 查询性能: 需优化 (>100ms)")
    
    # 检查分片均衡
    dist_values = list(results['distribution'].values())
    if dist_values:
        max_diff = max(dist_values) - min(dist_values)
        avg_val = sum(dist_values) / len(dist_values)
        if max_diff / avg_val < 0.2:
            print("✓ 分片均衡: 优秀 (偏差<20%)")
        elif max_diff / avg_val < 0.5:
            print("✓ 分片均衡: 良好 (偏差<50%)")
        else:
            print("⚠ 分片均衡: 需优化 (偏差>50%)")
    
    print("\n测试完成！")

if __name__ == '__main__':
    main()
