import logging
from datetime import datetime
from typing import List

import clickhouse_connect
from clickhouse_connect.driver import Client

from src.core.config import settings
from src.models.metrics import RepoMetrics

logger = logging.getLogger(__name__)


class ClickHouseDAO:
    """
    ClickHouse 数据访问层，提供另类数据（GitHub 指标、硬件现货价格、政企招投标）的建表与批量写入接口。
    """

    def __init__(self):
        self.host = settings.CLICKHOUSE_HOST
        self.port = settings.CLICKHOUSE_PORT
        self.user = settings.CLICKHOUSE_USER
        self.password = settings.CLICKHOUSE_PASSWORD
        self.database = settings.CLICKHOUSE_DB
        self._client: Client | None = None

    def get_client(self) -> Client:
        """由于 clickhouse_connect 依靠 urllib3，它有内置线程池，不支持完全的 asyncio。但在 FastAPI 中以后台任务写入通常足够。"""
        if not self._client:
            self._client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
            )
        return self._client

    def init_database_and_tables(self):
        """初始化数据库和所需的表"""
        client = self.get_client()

        # 建库
        client.command(f"CREATE DATABASE IF NOT EXISTS {self.database}")

        # 建表 1: 原始采集指标表 (保留 1 年)
        create_metrics_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.database}.github_repo_metrics
        (
            `collect_time` DateTime,
            `org` String,
            `repo` String,
            `label` String,
            `pr_merged_count` UInt32,
            `pr_merged_acceleration` Int32,
            `issue_close_median_hours` Float64,
            `star_delta_7d` Int32,
            `commit_count_7d` UInt32,
            `contributor_count_30d` UInt32
        )
        ENGINE = MergeTree()
        ORDER BY (label, org, repo, collect_time)
        TTL collect_time + INTERVAL 1 YEAR
        """
        client.command(create_metrics_table_sql)

        # 建表 2: 生态信号聚类结果表 (保留 1 年)
        create_signals_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.database}.ecosystem_signals
        (
            `signal_time` DateTime,
            `label` String,
            `composite_z_score` Float64,
            `dominant_factor` String,
            `signal_level` Enum8('NEUTRAL'=0, 'WARM'=1, 'HOT'=2, 'EXTREME'=3),
            `detail` String
        )
        ENGINE = MergeTree()
        ORDER BY (label, signal_time)
        TTL signal_time + INTERVAL 1 YEAR
        """
        client.command(create_signals_table_sql)

        # 建表 3: 硬件算力现货价格表 (新增 Story 18.1)
        create_hardware_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.database}.hardware_spot_prices
        (
            `collect_time` DateTime,
            `platform` String,
            `gpu_model` String,
            `instance_type` String,
            `price_per_hour` Float64,
            `availability` Float64
        )
        ENGINE = MergeTree()
        ORDER BY (platform, gpu_model, collect_time)
        TTL collect_time + INTERVAL 1 YEAR
        """
        client.command(create_hardware_table_sql)

        # 建表 4: 政企招投标算力投资表 (新增 Story 18.2)
        create_procurement_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.database}.hardware_procurement_capex
        (
            `date` Date,
            `title` String,
            `purchaser` String,
            `winner` String,
            `hardware_type` String,
            `amount` Float64,
            `region` String,
            `collect_time` DateTime
        )
        ENGINE = MergeTree()
        ORDER BY (hardware_type, date, winner)
        TTL collect_time + INTERVAL 3 YEAR
        """
        client.command(create_procurement_table_sql)

        logger.info(f"Initialized ClickHouse database '{self.database}' and tables.")

    def insert_metrics(self, metrics: List[RepoMetrics]):
        """批量插入 Github 采集对象"""
        if not metrics:
            return

        client = self.get_client()
        data = [
            [
                m.collect_time.replace(tzinfo=None),
                m.org,
                m.repo,
                m.label,
                m.pr_merged_count,
                m.pr_merged_acceleration,
                m.issue_close_median_hours,
                m.star_delta_7d,
                m.commit_count_7d,
                m.contributor_count_30d,
            ]
            for m in metrics
        ]

        columns = [
            "collect_time", "org", "repo", "label", "pr_merged_count",
            "pr_merged_acceleration", "issue_close_median_hours", 
            "star_delta_7d", "commit_count_7d", "contributor_count_30d"
        ]

        client.insert(
            table="github_repo_metrics",
            data=data,
            column_names=columns,
            database=self.database
        )
        logger.info(f"Inserted {len(metrics)} repo metrics into ClickHouse.")

    def insert_hardware_prices(self, prices: List):
        """批量插入硬件价格对象 (HardwareSpotPrice)"""
        if not prices:
            return

        client = self.get_client()
        data = [
            [
                p.collect_time.replace(tzinfo=None),
                p.platform,
                p.gpu_model,
                p.instance_type,
                p.price_per_hour,
                p.availability,
            ]
            for p in prices
        ]

        columns = [
            "collect_time", "platform", "gpu_model", 
            "instance_type", "price_per_hour", "availability"
        ]

        client.insert(
            table="hardware_spot_prices",
            data=data,
            column_names=columns,
            database=self.database
        )
        logger.info(f"Inserted {len(prices)} hardware prices into ClickHouse.")

    def insert_procurement_tenders(self, tenders: List):
        """批量插入招投标公告对象 (HardwareProcurementTender)"""
        if not tenders:
            return

        client = self.get_client()
        data = [
            [
                p.date.date() if isinstance(p.date, datetime) else p.date,
                p.title,
                p.purchaser,
                p.winner,
                p.hardware_type,
                p.amount,
                p.region,
                p.collect_time.replace(tzinfo=None),
            ]
            for p in tenders
        ]

        columns = [
            "date", "title", "purchaser", "winner", 
            "hardware_type", "amount", "region", "collect_time"
        ]

        client.insert(
            table="hardware_procurement_capex",
            data=data,
            column_names=columns,
            database=self.database
        )
        logger.info(f"Inserted {len(tenders)} procurement tenders into ClickHouse.")
