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
        self.redis_client = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
        
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
    
    def run_export(self):
        """执行完整导出流程"""
        logger.info("=" * 60)
        logger.info("🚀 开始监控数据导出...")
        logger.info("=" * 60)
        
        try:
            # 连接云端数据库
            self.connect_cloud_mysql()
            
            # 导出各类数据
            self.export_prometheus_metrics()
            self.export_clickhouse_replication()
            self.export_redis_status()
            self.export_gost_tunnel_status()
            self.export_system_resources()
            
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
