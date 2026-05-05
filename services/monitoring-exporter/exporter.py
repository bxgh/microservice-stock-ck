"""
监控数据导出服务
将本地 Prometheus、ClickHouse、Redis 监控数据导出到腾讯云 MySQL
供 Grafana Cloud 远程访问

Author: AI Agent
Date: 2026-01-05
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any
import pymysql
from prometheus_api_client import PrometheusConnect
from clickhouse_driver import Client as ClickHouseClient
import redis
import subprocess
import requests
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MonitoringExporter:
    """监控数据导出器"""
    
    def __init__(self):
        # 本地数据源
        self.prom = PrometheusConnect(url="http://127.0.0.1:9091")
        self.clickhouse = ClickHouseClient(host='127.0.0.1', port=9000)
        self.redis_client = redis.Redis(host='127.0.0.1', port=6379, password='redis123', decode_responses=True)
        
        # 云端 MySQL (通过 GOST 隧道)
        self.cloud_db = None
    
    def connect_cloud_mysql(self):
        """连接腾讯云 MySQL"""
        try:
            self.cloud_db = pymysql.connect(
                host='127.0.0.1',
                port=36301,  # GOST MySQL 隧道
                user='root',
                password='alwaysup@888',
                database='monitoring',
                charset='utf8mb4',
                autocommit=False,
                connect_timeout=10
            )
            logger.info("✅ 连接腾讯云 MySQL 成功")
        except Exception as e:
            logger.error(f"❌ 连接腾讯云 MySQL 失败: {e}")
            raise
    
    def export_prometheus_metrics(self):
        """导出 Prometheus 关键指标"""
        logger.info("📊 开始导出 Prometheus 指标...")
        
        metrics_to_export = [
            'clickhouse_replication_lag_seconds',
            'redis_memory_used_bytes',
            'gost_tunnel_health',
            'node_cpu_seconds_total',
            'node_memory_MemAvailable_bytes'
        ]
        
        cursor = self.cloud_db.cursor()
        timestamp = datetime.now()
        exported_count = 0
        
        try:
            for metric_name in metrics_to_export:
                try:
                    # 查询最新值
                    result = self.prom.custom_query(metric_name)
                    
                    for series in result:
                        metric_value = float(series['value'][1])
                        labels = series['metric']
                        
                        cursor.execute(
                            """INSERT INTO metrics_timeseries 
                               (metric_name, metric_value, labels, timestamp) 
                               VALUES (%s, %s, %s, %s)""",
                            (metric_name, metric_value, str(labels), timestamp)
                        )
                        exported_count += 1
                
                except Exception as e:
                    logger.warning(f"⚠️ 导出指标 {metric_name} 失败: {e}")
            
            self.cloud_db.commit()
            logger.info(f"✅ Prometheus 指标导出完成: {exported_count} 条")
        
        except Exception as e:
            self.cloud_db.rollback()
            logger.error(f"❌ Prometheus 指标导出失败: {e}")
            raise
        finally:
            cursor.close()
    
    def export_clickhouse_replication(self):
        """导出 ClickHouse 复制状态"""
        logger.info("🗄️ 开始导出 ClickHouse 复制状态...")
        
        query = """
        SELECT 
            database,
            table,
            is_readonly,
            absolute_delay,
            queue_size
        FROM system.replicas
        """
        
        cursor = self.cloud_db.cursor()
        timestamp = datetime.now()
        
        try:
            result = self.clickhouse.execute(query)
            
            for row in result:
                cursor.execute(
                    """INSERT INTO clickhouse_replication 
                       (server, database_name, table_name, is_readonly, 
                        absolute_delay, queue_size, timestamp) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    ('server41', row[0], row[1], row[2], row[3], row[4], timestamp)
                )
            
            self.cloud_db.commit()
            logger.info(f"✅ ClickHouse 复制状态导出完成: {len(result)} 条")
        
        except Exception as e:
            self.cloud_db.rollback()
            logger.error(f"❌ ClickHouse 复制状态导出失败: {e}")
            raise
        finally:
            cursor.close()
    
    def export_redis_status(self):
        """导出 Redis 状态"""
        logger.info("💾 开始导出 Redis 状态...")
        
        cursor = self.cloud_db.cursor()
        timestamp = datetime.now()
        
        try:
            # 获取 Redis 内存信息
            info = self.redis_client.info('memory')
            stats = self.redis_client.info('stats')
            clients = self.redis_client.info('clients')
            
            used_memory_mb = info['used_memory'] / (1024 * 1024)
            max_memory_mb = info.get('maxmemory', 0) / (1024 * 1024)
            memory_usage_percent = (used_memory_mb / max_memory_mb * 100) if max_memory_mb > 0 else 0
            
            cursor.execute(
                """INSERT INTO redis_status 
                   (used_memory_mb, max_memory_mb, memory_usage_percent, 
                    connected_clients, ops_per_sec, timestamp) 
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (used_memory_mb, max_memory_mb, memory_usage_percent,
                 clients['connected_clients'], 
                 stats.get('instantaneous_ops_per_sec', 0),
                 timestamp)
            )
            
            self.cloud_db.commit()
            logger.info(f"✅ Redis 状态导出完成: {used_memory_mb:.2f}MB / {max_memory_mb:.2f}MB")
        
        except Exception as e:
            self.cloud_db.rollback()
            logger.error(f"❌ Redis 状态导出失败: {e}")
            raise
        finally:
            cursor.close()
    
    def export_gost_tunnel_status(self):
        """导出 GOST 隧道状态"""
        logger.info("🚇 开始导出 GOST 隧道状态...")
        
        import subprocess
        
        cursor = self.cloud_db.cursor()
        timestamp = datetime.now()
        
        try:
            # 检查 GOST 服务状态
            tunnels = [
                'gost-foreign',
                'gost-domestic',
                'gost-mysql-tunnel'
            ]
            
            for tunnel_name in tunnels:
                try:
                    result = subprocess.run(
                        ['systemctl', 'is-active', f'{tunnel_name}.service'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    is_healthy = 1 if result.stdout.strip() == 'active' else 0
                    
                    cursor.execute(
                        """INSERT INTO gost_tunnel_status 
                           (tunnel_name, is_healthy, last_check_time, timestamp) 
                           VALUES (%s, %s, %s, %s)""",
                        (tunnel_name, is_healthy, timestamp, timestamp)
                    )
                
                except Exception as e:
                    logger.warning(f"⚠️ 检查隧道 {tunnel_name} 失败: {e}")
            
            self.cloud_db.commit()
            logger.info(f"✅ GOST 隧道状态导出完成")
        
        except Exception as e:
            self.cloud_db.rollback()
            logger.error(f"❌ GOST 隧道状态导出失败: {e}")
            raise
        finally:
            cursor.close()
    
    def export_system_resources(self):
        """导出系统资源使用"""
        logger.info("💻 开始导出系统资源使用...")
        
        import psutil
        
        cursor = self.cloud_db.cursor()
        timestamp = datetime.now()
        
        try:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用
            memory = psutil.virtual_memory()
            memory_total_gb = memory.total / (1024**3)
            memory_used_gb = memory.used / (1024**3)
            
            # 磁盘使用
            disk = psutil.disk_usage('/')
            disk_total_gb = disk.total / (1024**3)
            disk_used_gb = disk.used / (1024**3)
            
            cursor.execute(
                """INSERT INTO system_resources 
                   (server, cpu_usage_percent, memory_total_gb, memory_used_gb,
                    disk_total_gb, disk_used_gb, timestamp) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                ('server41', cpu_percent, memory_total_gb, memory_used_gb,
                 disk_total_gb, disk_used_gb, timestamp)
            )
            
            self.cloud_db.commit()
            logger.info(f"✅ 系统资源导出完成: CPU {cpu_percent}%, MEM {memory_used_gb:.1f}GB")
        
        except Exception as e:
            self.cloud_db.rollback()
            logger.error(f"❌ 系统资源导出失败: {e}")
            raise
        finally:
            cursor.close()
    
    def export_server58_resources(self):
        """通过 SSH 导出 58 服务器资源使用"""
        logger.info("🖥️ 开始导出 Server 58 资源使用 (SSH)...")
        
        cursor = self.cloud_db.cursor()
        timestamp = datetime.now()
        
        try:
            # SSH 命令获取 CPU、内存、磁盘
            ssh_cmd = """
            python3 -c "
import psutil
import json
result = {
    'cpu': psutil.cpu_percent(interval=1),
    'mem_total': psutil.virtual_memory().total / (1024**3),
    'mem_used': psutil.virtual_memory().used / (1024**3),
    'disk_total': psutil.disk_usage('/').total / (1024**3),
    'disk_used': psutil.disk_usage('/').used / (1024**3)
}
print(json.dumps(result))
"
            """
            
            result = subprocess.run(
                ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', 
                 '192.168.151.58', ssh_cmd],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout.strip())
                
                cursor.execute(
                    """INSERT INTO system_resources 
                       (server, cpu_usage_percent, memory_total_gb, memory_used_gb,
                        disk_total_gb, disk_used_gb, timestamp) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    ('server58', data['cpu'], data['mem_total'], data['mem_used'],
                     data['disk_total'], data['disk_used'], timestamp)
                )
                
                self.cloud_db.commit()
                logger.info(f"✅ Server 58 资源导出完成: CPU {data['cpu']}%, MEM {data['mem_used']:.1f}GB")
            else:
                logger.warning(f"⚠️ SSH 到 Server 58 失败: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            logger.error("❌ SSH 到 Server 58 超时")
        except Exception as e:
            self.cloud_db.rollback()
            logger.error(f"❌ Server 58 资源导出失败: {e}")
        finally:
            cursor.close()
    
    def export_service_health(self):
        """导出微服务健康状态"""
        logger.info("🏥 开始导出微服务健康状态...")
        
        services = [
            ('get-stockdata', 'http://127.0.0.1:8083/api/v1/health'),
            ('quant-strategy', 'http://127.0.0.1:8084/api/v1/health'),
            ('task-orchestrator', 'http://127.0.0.1:18000/health'),
            ('mootdx-api', 'http://127.0.0.1:8003/api/v1/health'),
        ]
        
        cursor = self.cloud_db.cursor()
        timestamp = datetime.now()
        
        try:
            for service_name, url in services:
                try:
                    resp = requests.get(url, timeout=5)
                    is_healthy = 1 if resp.status_code == 200 else 0
                    response_time_ms = resp.elapsed.total_seconds() * 1000
                except Exception as e:
                    is_healthy = 0
                    response_time_ms = -1
                    logger.warning(f"⚠️ 服务 {service_name} 健康检查失败: {e}")
                
                cursor.execute(
                    """INSERT INTO service_health 
                       (service_name, is_healthy, response_time_ms, timestamp) 
                       VALUES (%s, %s, %s, %s)""",
                    (service_name, is_healthy, response_time_ms, timestamp)
                )
            
            self.cloud_db.commit()
            logger.info(f"✅ 微服务健康状态导出完成: {len(services)} 个服务")
        
        except Exception as e:
            self.cloud_db.rollback()
            logger.error(f"❌ 微服务健康状态导出失败: {e}")
        finally:
            cursor.close()
    
    def export_docker_status(self):
        """导出 Docker 容器状态"""
        logger.info("🐳 开始导出 Docker 容器状态...")
        
        cursor = self.cloud_db.cursor()
        timestamp = datetime.now()
        
        try:
            result = subprocess.run(
                ['docker', 'ps', '-a', '--format', '{{.Names}}|{{.Status}}|{{.Image}}'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    parts = line.split('|')
                    if len(parts) >= 2:
                        container_name = parts[0]
                        status = parts[1]
                        image = parts[2] if len(parts) > 2 else ''
                        
                        # 判断是否运行中
                        is_running = 1 if 'Up' in status else 0
                        
                        cursor.execute(
                            """INSERT INTO docker_status 
                               (server, container_name, status, image, is_running, timestamp) 
                               VALUES (%s, %s, %s, %s, %s, %s)""",
                            ('server41', container_name, status[:100], image[:100], 
                             is_running, timestamp)
                        )
                
                self.cloud_db.commit()
                logger.info(f"✅ Docker 容器状态导出完成")
            else:
                logger.warning(f"⚠️ docker ps 命令失败: {result.stderr}")
        
        except Exception as e:
            self.cloud_db.rollback()
            logger.error(f"❌ Docker 容器状态导出失败: {e}")
        finally:
            cursor.close()
    
    def export_clickhouse_business_metrics(self):
        """导出 ClickHouse 业务指标"""
        logger.info("📈 开始导出 ClickHouse 业务指标...")
        
        cursor = self.cloud_db.cursor()
        timestamp = datetime.now()
        
        try:
            # 1. K线数据量
            # 使用 formatDateTime 确保日期对比正确
            today_str = datetime.now().strftime('%Y%m%d')
            
            # 修正 ClickHouse 表 stock_data.stock_kline_daily 中的字段名为 stock_code
            kline_today = self.clickhouse.execute(
                f"SELECT count() FROM stock_data.stock_kline_daily WHERE trade_date = '{today_str}'"
            )[0][0]
            
            kline_total = self.clickhouse.execute(
                "SELECT count() FROM stock_data.stock_kline_daily"
            )[0][0]
            
            stock_count = self.clickhouse.execute(
                f"SELECT countDistinct(stock_code) FROM stock_data.stock_kline_daily WHERE trade_date >= today() - 7"
            )[0][0]
            
            # 2. 分笔数据量
            tick_today = self.clickhouse.execute(
                f"SELECT countDistinct(stock_code) FROM stock_data.tick_data WHERE trade_date = '{today_str}'"
            )[0][0]
            
            # 3. 快照数据量 - 这里检查 ClickHouse 的 snapshot_data 表
            snapshot_today = self.clickhouse.execute(
                f"SELECT count() FROM stock_data.snapshot_data WHERE trade_date = '{today_str}'"
            )[0][0]
            
            # 4. 预期股票数 (从 Redis 获取)
            tick_expected = self.redis_client.scard('stock_list:active') or 5300
            
            # 5. 覆盖率计算
            kline_coverage_rate = float(round(stock_count / 5300 * 100, 2))
            tick_coverage_rate = float(round(tick_today / tick_expected * 100, 2)) if tick_expected > 0 else 0
            
            # 6. 沪深300覆盖
            # HS300 成分股在 ClickHouse 中的表是 stock_data.hs300_constituents
            # 增加 defensive 检查，防止表不存在导致整个导出失败
            hs300_kline = 0
            hs300_tick = 0
            
            try:
                # 检查是否存在 hs300_constituents 表，如果不存在则从其它表近似推导或设为 0
                tables = [t[0] for t in self.clickhouse.execute("SHOW TABLES FROM stock_data")]
                if 'hs300_constituents' in tables:
                    hs300_kline = self.clickhouse.execute(f"""
                        SELECT countDistinct(stock_code) FROM stock_data.stock_kline_daily 
                        WHERE trade_date >= '{today_str}' AND stock_code IN (
                            SELECT ts_code FROM stock_data.hs300_constituents
                        )
                    """)[0][0]
                    
                    hs300_tick = self.clickhouse.execute(f"""
                        SELECT countDistinct(stock_code) FROM stock_data.tick_data 
                        WHERE trade_date = '{today_str}' AND stock_code IN (
                            SELECT ts_code FROM stock_data.hs300_constituents
                        )
                    """)[0][0]
                else:
                    logger.warning("⚠️ 沪深300成分股表不存在，跳过覆盖率检查")
            except Exception as e:
                logger.warning(f"⚠️ 沪深300覆盖检查失败: {e}")
            
            cursor.execute(
                """INSERT INTO clickhouse_business_metrics 
                   (kline_today, kline_total, snapshot_today, stock_count, 
                    tick_today, tick_expected, kline_coverage_rate, tick_coverage_rate,
                    hs300_kline, hs300_tick, timestamp) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (kline_today, kline_total, snapshot_today, stock_count,
                 tick_today, tick_expected, kline_coverage_rate, tick_coverage_rate,
                 hs300_kline, hs300_tick, timestamp)
            )
            
            self.cloud_db.commit()
            logger.info(f"✅ ClickHouse 业务指标完成: K线覆盖 {kline_coverage_rate}%, 分笔覆盖 {tick_coverage_rate}%")
        
        except Exception as e:
            self.cloud_db.rollback()
            logger.error(f"❌ ClickHouse 业务指标导出失败: {e}")
        finally:
            cursor.close()

    def export_task_execution_status(self):
        """导出任务执行告警状态"""
        logger.info("📡 开始监控任务执行状态...")
        
        # 使用 correct Cursor 类型
        cursor = self.cloud_db.cursor(pymysql.cursors.DictCursor)
        timestamp = datetime.now()
        
        try:
            # 直接从云端 MySQL 的 alwaysup.sync_execution_logs 采集失败记录
            # 修正字段名: task_name, execution_time, details
            sql = """
                SELECT `task_name`, `status`, `details`, `execution_time`
                FROM `alwaysup`.`sync_execution_logs`
                WHERE `status` IN ('FAILED', 'TIMEOUT', 'FAILURE')
                AND `execution_time` > DATE_SUB(NOW(), INTERVAL 30 MINUTE)
            """
            cursor.execute(sql)
            failures = cursor.fetchall()
            
            for f in failures:
                # 插入到云端监测库 monitoring 的告警表
                # 使用 INSERT IGNORE 避免重复告警，因为我们已经对 (task_id, detected_at) 加了唯一索引
                # 这里将 task_name 作为 task_id 存入
                cursor.execute(
                    """INSERT IGNORE INTO `monitoring`.`task_execution_alerts` 
                       (`task_id`, `task_name`, `status`, `error_message`, `detected_at`)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (f['task_name'], f['task_name'], f['status'], f['details'], f['execution_time'])
                )
            
            self.cloud_db.commit()
            if failures:
                logger.warning(f"🚨 发现 {len(failures)} 条任务失败记录已同步到告警表")
            else:
                logger.info("✅ 未发现新增任务失败记录")
                
        except Exception as e:
            self.cloud_db.rollback()
            logger.error(f"❌ 任务执行状态监控失败: {e}")
        finally:
            cursor.close()
    
    def run_export(self):
        """执行完整导出流程"""
        logger.info("=" * 60)
        logger.info("🚀 开始监控数据导出...")
        logger.info("=" * 60)
        
        try:
            # 连接云端数据库
            self.connect_cloud_mysql()
            
            # L0: 生死监控 (GOST 隧道)
            self.export_gost_tunnel_status()
            
            # L1: 资源水位 (41 + 58)
            self.export_system_resources()
            self.export_server58_resources()
            self.export_redis_status()
            
            # L2: 复制与同步
            self.export_clickhouse_replication()
            
            # L3: 服务健康
            self.export_service_health()
            self.export_docker_status()
            
            # L4: 业务指标
            self.export_clickhouse_business_metrics()
            self.export_task_execution_status()
            
            # 其他 Prometheus 指标
            self.export_prometheus_metrics()
            
            logger.info("=" * 60)
            logger.info("✅ 监控数据导出完成！")
            logger.info("=" * 60)
        
        except Exception as e:
            logger.error(f"❌ 监控数据导出失败: {e}")
            raise
        
        finally:
            if self.cloud_db:
                self.cloud_db.close()
                logger.info("🔌 云端 MySQL 连接已关闭")


async def main_loop():
    """持续运行导出任务"""
    exporter = MonitoringExporter()
    interval = 300  # 5 分钟
    
    logger.info(f"✨ 导出服务启动，每 {interval} 秒同步一次数据")
    
    while True:
        try:
            start_time = datetime.now()
            exporter.run_export()
            elapsed = (datetime.now() - start_time).total_seconds()
            sleep_time = max(0, interval - elapsed)
            
            logger.info(f"😴 等待 {sleep_time:.1f} 秒进行下一次同步...")
            await asyncio.sleep(sleep_time)
            
        except KeyboardInterrupt:
            logger.info("🛑 服务正在停止...")
            break
        except Exception as e:
            logger.error(f"❌ 运行循环出错: {e}")
            await asyncio.sleep(60)  # 出错后等待 1 分钟重试


if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        pass
