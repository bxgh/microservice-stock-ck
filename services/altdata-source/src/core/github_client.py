import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class GitHubClientError(Exception):
    """GitHub API 调用错误基类"""
    pass


class TokenExhaustedError(GitHubClientError):
    """所有 Token 配额均已耗尽"""
    pass


class GitHubClient:
    """
    支持 Token 自动轮换、请求重试的异步 GitHub API 客户端。
    """
    
    def __init__(self, tokens: List[str]):
        if not tokens:
            raise ValueError("至少需要提供 1 个 GitHub PAT (Personal Access Token)")
        self._tokens = tokens
        self._current_index = 0
        proxy_url = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
        if proxy_url:
            logger.info(f"GitHubClient initialized with proxy: {proxy_url}")
            self._client = httpx.AsyncClient(timeout=10.0, proxy=proxy_url)
        else:
            self._client = httpx.AsyncClient(timeout=10.0)

    @property
    def current_token(self) -> str:
        return self._tokens[self._current_index]

    def _rotate_token(self) -> str:
        """切换到下一个 token"""
        self._current_index = (self._current_index + 1) % len(self._tokens)
        logger.info(f"Switched to GitHub token slice #{self._current_index}")
        return self.current_token
        
    async def close(self):
        """释放连接池资源"""
        await self._client.aclose()

    async def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, retry: int = 3
    ) -> httpx.Response:
        """
        执行 GET 请求。如果遇到 Rate Limit 引发的 403 (且 X-RateLimit-Remaining 归零)，
        则自动切换 Token 后重试。对于 5xx 错误执行指数退避重试。
        """
        if not endpoint.startswith("http"):
            url = f"https://api.github.com{endpoint}"
        else:
            url = endpoint

        attempt = 0
        last_error = None
        
        while attempt < retry:
            headers = {
                "Authorization": f"Bearer {self.current_token}",
                "Accept": "application/vnd.github.v3+json",
            }
            try:
                response = await self._client.get(url, params=params, headers=headers)
                
                # 限流处理
                if response.status_code == 403:
                    remaining = response.headers.get("X-RateLimit-Remaining")
                    if remaining == "0":
                        logger.warning(
                            f"Token #{self._current_index} rate limit exhausted. Rotating..."
                        )
                        # 如果所有 token 都在这轮里试过了，抛出特定异常
                        if attempt >= len(self._tokens):
                            raise TokenExhaustedError("All GitHub tokens exhausted")
                        self._rotate_token()
                        attempt += 1
                        continue

                # 服务端级抖动重试
                if response.status_code >= 500:
                    attempt += 1
                    backoff = 2 ** attempt
                    logger.warning(f"GitHub 5xx error on {url}. Retry in {backoff}s...")
                    await asyncio.sleep(backoff)
                    continue
                    
                # 正常或其他 4xx 错误直接返回，交由业务解析
                return response
                
            except httpx.RequestError as e:
                attempt += 1
                backoff = 2 ** attempt
                logger.warning(f"Request error: {e}. Retry in {backoff}s...")
                last_error = e
                await asyncio.sleep(backoff)
        
        raise GitHubClientError(f"Request failed after {retry} retries: {last_error}")

    async def get_paginated(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, max_pages: int = 5
    ) -> List[Dict[str, Any]]:
        """
        自动处理 GitHub 的 Link 首部分页 (page=1,2,3...)，返回合并的 List。
        """
        all_items = []
        p = params.copy() if params else {}
        
        # 默认每页最大化拉取限制
        if "per_page" not in p:
            p["per_page"] = 100
            
        page = p.get("page", 1)
        pages_fetched = 0
        
        while pages_fetched < max_pages:
            p["page"] = page
            response = await self.get(endpoint, params=p)
            
            # 若结果是 404 等，记录并中断分页
            if response.status_code != 200:
                logger.error(
                    f"Paginated GET {endpoint} failed with {response.status_code}: {response.text}"
                )
                break
                
            data = response.json()
            if not isinstance(data, list):
                # 不是标准分页数组格式，强行终止
                all_items.append(data)
                break
                
            all_items.extend(data)
            
            # 检查是否有下一页
            if "next" not in response.links:
                break
                
            page += 1
            pages_fetched += 1
            
        return all_items
