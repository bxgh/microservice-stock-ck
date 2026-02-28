from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.models.metrics import RepoMetrics
from src.storage.clickhouse import ClickHouseDAO


@patch("src.storage.clickhouse.clickhouse_connect.get_client")
def test_init_database_and_tables(mock_get_client):
    """验证是否调用了预期的 DDL CREATE 语句"""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    dao = ClickHouseDAO()
    dao.init_database_and_tables()
    
    # 建库 + 建表 x 2，期望 3 次 command 调用
    assert mock_client.command.call_count == 3
    
    # 抽查是否调用了建表语句
    calls = mock_client.command.call_args_list
    db_create = calls[0][0][0]
    tb1_create = calls[1][0][0]
    tb2_create = calls[2][0][0]
    
    assert "CREATE DATABASE IF NOT EXISTS" in db_create
    assert "github_repo_metrics" in tb1_create
    assert "ecosystem_signals" in tb2_create


@patch("src.storage.clickhouse.clickhouse_connect.get_client")
def test_insert_metrics(mock_get_client):
    """测试数据正确组装到了批量写入 client.insert 列表中"""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    dao = ClickHouseDAO()
    
    dummy_date = datetime(2026, 2, 28, 12, 0, tzinfo=timezone.utc)
    metrics = [
        RepoMetrics(
            org="test_org",
            repo="test_repo",
            label="test_label",
            pr_merged_count=10,
            pr_merged_acceleration=5,
            issue_close_median_hours=2.5,
            star_delta_7d=100,
            commit_count_7d=20,
            contributor_count_30d=5,
            collect_time=dummy_date
        )
    ]
    
    dao.insert_metrics(metrics)
    
    assert mock_client.insert.called
    
    # 校验插表方法调用的参数
    args, kwargs = mock_client.insert.call_args
    assert kwargs["table"] == "github_repo_metrics"
    
    data = kwargs["data"]
    assert len(data) == 1
    assert data[0][1] == "test_org"  # column org
    assert data[0][3] == "test_label"  # column label
    # 注意 timezone info被剔除，这里验证值
    assert data[0][0] == dummy_date.replace(tzinfo=None)
