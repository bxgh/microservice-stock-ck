import json
from datetime import datetime, timezone

import pytest
import respx
from httpx import Response

from src.collectors.github import GitHubCollector
from src.core.github_client import GitHubClient


@pytest.fixture
def mock_client():
    return GitHubClient(tokens=["fake_token"])


@pytest.mark.asyncio
@respx.mock
async def test_collector_issue_median(mock_client):
    collector = GitHubCollector(mock_client)
    # mock 时间以保证测试稳定性
    collector.now = datetime(2026, 2, 28, 12, 0, tzinfo=timezone.utc)
    
    q_url = "https://api.github.com/search/issues"
    
    # 模拟返回：三个 issues。时长分别为：
    # issue1: 1个小时
    # issue2: 2个小时 
    # issue3: 3个小时
    
    mock_response = {
        "items": [
            {
                "created_at": "2026-02-27T12:00:00Z",
                "closed_at": "2026-02-27T13:00:00Z",  # 1hr
            },
            {
                "created_at": "2026-02-26T10:00:00Z",
                "closed_at": "2026-02-26T12:00:00Z",  # 2hr
            },
            {
                "created_at": "2026-02-25T01:00:00Z",
                "closed_at": "2026-02-25T04:00:00Z",  # 3hr
            }
        ]
    }
    
    respx.get(q_url).mock(return_value=Response(200, json=mock_response))
    
    median_hrs = await collector._get_issue_median_close_time("test_org", "test_repo")
    
    # [1.0, 2.0, 3.0] 的中位数应该是 2.0
    assert median_hrs == 2.0


@pytest.mark.asyncio
@respx.mock
async def test_collector_pr_acceleration(mock_client):
    collector = GitHubCollector(mock_client)
    collector.now = datetime(2026, 2, 28, 12, 0, tzinfo=timezone.utc)
    
    q_url = "https://api.github.com/search/issues"
    
    # 我们用 side_effect 来响应两次调用。第一次是查询 7天内的 merged PR (返回 50) 
    # 第一次是查询 14天到 7天的 merged PR (返回 30)
    respx.get(q_url).mock(
        side_effect=[
            Response(200, json={"total_count": 50}),
            Response(200, json={"total_count": 30}),
        ]
    )
    
    result = await collector._get_pr_metrics("test_org", "test_repo")
    
    # 算术预期: acceleration = 50 - 30 = 20
    assert result["current_7d_count"] == 50
    assert result["acceleration"] == 20
