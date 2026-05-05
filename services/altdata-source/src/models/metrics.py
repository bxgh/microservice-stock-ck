from datetime import datetime
from pydantic import BaseModel


class RepoMetrics(BaseModel):
    """单个 GitHub 仓库提取出的多维特征"""
    org: str
    repo: str
    label: str  # 关联同花顺概念使用，例如 'deepseek', 'paddle'
    
    # 7天内合并的 pull requests 总数
    pr_merged_count: int
    
    # PR 加速度：最近7日内的数量 - 过去 14天到7天的数量
    pr_merged_acceleration: int
    
    # 近 30 天 closed 的 issue 中位数耗时（小时，表征社区响应度）
    issue_close_median_hours: float
    
    # 7天内新增关注
    star_delta_7d: int
    
    # 最近7天主分支（default_branch） commit 次数
    commit_count_7d: int
    
    # 近 30 天在仓库上有任何互动（提Issue、PR等）的独立排重用户数量
    contributor_count_30d: int
    
    # 数据采集基准时间
    collect_time: datetime
