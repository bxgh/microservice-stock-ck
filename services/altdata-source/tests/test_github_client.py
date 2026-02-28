import pytest
from src.core.github_client import GitHubClient, TokenExhaustedError

import respx
from httpx import Response


@pytest.mark.asyncio
@respx.mock
async def test_github_client_token_rotation():
    """测试 403 限流时 Token 能否正确被轮换并最终成功"""
    client = GitHubClient(tokens=["token1", "token2", "token3"])
    
    API_URL = "https://api.github.com/user"
    
    # 第一次请求：token1 限流
    route = respx.get(API_URL).mock(
        side_effect=[
            Response(403, headers={"X-RateLimit-Remaining": "0"}),
            Response(403, headers={"X-RateLimit-Remaining": "0"}),
            Response(200, json={"login": "octocat"})
        ]
    )
    
    response = await client.get("/user")
    
    assert response.status_code == 200
    assert response.json() == {"login": "octocat"}
    # 断言发生了 3 次调用，意味着 token1, token2 都尝试并被跳过，最终在 token3 (或轮换中某一个) 成功
    assert route.call_count == 3
    
    # 此时 current_token 应由于旋转 2 次，由于有三个 token，变成 "token3" (index = 2)
    assert client.current_token == "token3"


@pytest.mark.asyncio
@respx.mock
async def test_github_client_token_exhausted():
    """测试所有 token 限流耗尽的情境，是否抛出对应 TokenExhaustedError"""
    # 这里用 2 个 tokens 模拟
    client = GitHubClient(tokens=["t1", "t2"])
    
    API_URL = "https://api.github.com/user"
    
    # 连续无停止的 403 轰炸
    respx.get(API_URL).mock(
        return_value=Response(403, headers={"X-RateLimit-Remaining": "0"})
    )
    
    with pytest.raises(TokenExhaustedError) as exc_info:
        await client.get("/user", retry=5)
        
    assert "exhausted" in str(exc_info.value)
