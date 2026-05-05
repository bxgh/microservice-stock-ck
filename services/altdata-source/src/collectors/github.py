import asyncio
import logging
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Optional

from src.core.github_client import GitHubClient, GitHubClientError
from src.models.metrics import RepoMetrics

logger = logging.getLogger(__name__)


class GitHubCollector:
    """
    提取 GitHub 给定组织仓库的关键开发与社区活跃特征。
    涵盖了拉取 PR, Issue, Commits 以及 Contributors 特点指标的计算。
    """
    def __init__(self, client: GitHubClient):
        self.client = client
        self.now = datetime.now(timezone.utc)

    async def collect_repo(self, org: str, repo: str, label: str) -> Optional[RepoMetrics]:
        """拉取全部 6 项指标并生成单个仓库的指标组装"""
        try:
            logger.info(f"Collecting metrics for {org}/{repo}")
            
            # 并发执行各个维度的特征数据获取
            (
                pr_stats, 
                issue_median_hours, 
                stars_7d, 
                commits_7d, 
                contributors_30d
            ) = await asyncio.gather(
                self._get_pr_metrics(org, repo),
                self._get_issue_median_close_time(org, repo),
                self._get_star_delta(org, repo),
                self._get_recent_commits(org, repo),
                self._get_active_contributors(org, repo),
                return_exceptions=False  # 若单项获取失败则通过 Exception 抛出中止该仓拉取以示警告
            )
            
            return RepoMetrics(
                org=org,
                repo=repo,
                label=label,
                pr_merged_count=pr_stats["current_7d_count"],
                pr_merged_acceleration=pr_stats["acceleration"],
                issue_close_median_hours=issue_median_hours,
                star_delta_7d=stars_7d,
                commit_count_7d=commits_7d,
                contributor_count_30d=contributors_30d,
                collect_time=self.now
            )
            
        except GitHubClientError as e:
            logger.error(f"Failed to fetch {org}/{repo} due to API/Token issue: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed processing {org}/{repo} unexpectedly: {e}")
            return None

    async def _get_pr_metrics(self, org: str, repo: str) -> dict:
        """
        1. 获取最近 7天的 merged PR数
        2. 获取 7~14天前的 merged PR数
        计算其差值作为 Acceleration
        """
        t_minus_7 = (self.now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        t_minus_14 = (self.now - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # GitHub Search API 查找符合最近 14 天合并条件的 PR。
        # 这里借助 Search API (`type:pr is:merged merged:>time`) 以最高效获得数目。
        # GitHub 的限制是不通过此法直接对 merged 过滤会导致海量分页提取负担。
        
        async def count_pr_since(start_time: str, end_time: Optional[str] = None) -> int:
            q = f"repo:{org}/{repo} is:pr is:merged merged:>={start_time}"
            if end_time:
                q += f" merged:<={end_time}"
            resp = await self.client.get("/search/issues", params={"q": q, "per_page": 1})
            data = resp.json()
            return data.get("total_count", 0)
        
        current_7d_count, prev_7d_count = await asyncio.gather(
            count_pr_since(t_minus_7),
            count_pr_since(t_minus_14, t_minus_7)
        )
        
        return {
            "current_7d_count": current_7d_count,
            "acceleration": current_7d_count - prev_7d_count
        }

    async def _get_issue_median_close_time(self, org: str, repo: str) -> float:
        """读取过去 30天内 close 的 Issue，计算其创建至关闭消耗的时间中位数（小时）"""
        t_minus_30 = (self.now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        q = f"repo:{org}/{repo} is:issue is:closed closed:>={t_minus_30}"
        
        # 考虑到 API 的分页负载，这里选取前 max_pages (如 300个 issues) 均可用作中位抽样。
        resp = await self.client.get("/search/issues", params={"q": q, "per_page": 100})
        data = resp.json()
        items = data.get("items", [])
        
        close_durations_hour = []
        for issue in items:
            # 过滤 PR 的干扰 (Search API 中 issue/PR 混合返回需要筛去 PR)
            if "pull_request" in issue:
                continue
            
            created = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
            closed = datetime.fromisoformat(issue["closed_at"].replace("Z", "+00:00"))
            
            hrs = (closed - created).total_seconds() / 3600.0
            if hrs >= 0:
                close_durations_hour.append(hrs)
        
        if not close_durations_hour:
            return 0.0
            
        return round(median(close_durations_hour), 2)

    async def _get_star_delta(self, org: str, repo: str) -> int:
        """
        通过 Stargazers API(Accept: application/vnd.github.v3.star+json)
        能得到 star 时间线，但非常缓慢（需遍历所有页）。
        优化方法：直接比对 7 天前和今天仓库总 Star 的差值几乎无法做到。
        这里改用近似：提取 /stargazers 并在过去 7天的时间跨度中计算星数。受限 pagination 此方法最多估算最近增持量。
        """
        t_minus_7 = self.now - timedelta(days=7)
        headers = {"Accept": "application/vnd.github.v3.star+json"}
        
        # 抓取最新的部分页数，直到遇到 7天以前 star 的时间戳为止。
        # 注: GitHub Client 需要传递 extra headers 但是目前未在框架提供，
        # 我们用 search/repositories 接口直接读取 stargazers_count 会更简易。但这只能拿到全额。
        
        # 变通替代实现：通过 /search/repositories 只能拿到当前总量，我们要差值。
        # 由于我们每天跑，在量化库里直接读取昨日 Star 就行，但由于目前纯无状态获取组件，
        # 我们暂采用一个近似值：搜索 created_at 最近 7 天提到这个库的讨论 / Issue 总量作为热度替代指标。
        # 由于必须强关联 Star，使用搜到 star 事件 (对于 Github 无能为力)，故此处将查最近 7天新增 fork 取代或记录0，
        # 在这我们返回0，或者根据实际每天入表后，由策略层 SQL 计算 delta。
        # 为符合本函数的语义，目前仅做 mock/占位实现。
        return 0

    async def _get_recent_commits(self, org: str, repo: str) -> int:
        """读取过去 7天所有 default_branch 的 Commits 数量"""
        t_minus_7 = (self.now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # GET /repos/{owner}/{repo}/commits?since=t_minus_7
        resp = await self.client.get(
            f"/repos/{org}/{repo}/commits", 
            params={"since": t_minus_7, "per_page": 100}
        )
        commits_data = resp.json()
        
        # 处理可能的异常
        if not isinstance(commits_data, list):
            return 0
            
        return len(commits_data)

    async def _get_active_contributors(self, org: str, repo: str) -> int:
        """
        返回近期参与者的估算。
        同样受限于 GitHub 没有 recent_contributors 接口，这里遍历最近 30 天 
        PR 与 Issue 的创建者，使用 Set 排重得出核心活跃人数。
        """
        t_minus_30 = (self.now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        q = f"repo:{org}/{repo} updated:>={t_minus_30}"
        
        resp = await self.client.get("/search/issues", params={"q": q, "per_page": 100})
        items = resp.json().get("items", [])
        
        users = set()
        for i in items:
            user = i.get("user")
            if user:
                users.add(user["login"])
                
        return len(users)
