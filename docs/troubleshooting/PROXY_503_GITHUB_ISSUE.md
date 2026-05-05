# GitHub 采集 503 代理阻断与 401 认证失败问题排查记录

## 问题现象
在 `altdata-source` 微服务尝试通过 GitHub API 采集数据时，遇到以下问题：
1. **网络连接失败**：服务无法通过现有的内部 HTTP 代理（`http://192.168.151.18:3128`）访问 GitHub API，返回 `503 Service Unavailable (ERR_CANNOT_FORWARD)`。
2. **认证失败**：移除代理后，返回 `401 Unauthorized` 错误。

## 根本原因
1. **代理阻断**：内部代理服务器（Squid）因配置或网络策略原因，无法打通至 `api.github.com` 的建立连接（CONNECT 隧道失败）。但直连（无需代理）可以正常访问外部网络（参考 `intraday-tick-collector` 容器的成功采集经验），表明系统所处网络环境可以直通部分海外 API。
2. **鉴权头异常**：`src/api/trigger.py` 在初始化 `GitHubClient` 时，错误地将 `settings.GITHUB_TOKENS` 这一环境变量字符串直传给了期望形式为 List 的入参 `tokens`，引起客户端对该字符串进行按字符的遍历并生成了错误的认证 Token 列表，导致鉴权失败（401）。

## 解决方案
### 1. 移除网络代理 (直连访问)
在服务端 `.env` 和环境配置中，**不要为访问 GitHub API 的微服务配置 `HTTP_PROXY` 和 `HTTPS_PROXY`**。
如果在被复用的 `docker-compose.yml` 或 `.env` 模板中有默认引入，需针对该特定工程移除它。
示例 `altdata-source/.env` 配置：
```env
# 移除以下原本全局复用的代理设置
# HTTP_PROXY="http://192.168.151.18:3128"
# HTTPS_PROXY="http://192.168.151.18:3128"
```
确保 Python 侧初始化的 `httpx.AsyncClient` 的 `proxy` 参数没有带入该失效的网关。

### 2. Token 安全加载解析
为保障配置安全与逻辑自洽，应在 Pydantic `BaseSettings` 端配置将字符串解析为所需列表的能力。
我们在 `src/core/config.py` 中应用或修复属性 `github_token_list`：
```python
    @property
    def github_token_list(self) -> List[str]:
        if not self.GITHUB_TOKENS:
            return []
        return [t.strip() for t in self.GITHUB_TOKENS.split(",") if t.strip()]
```
业务代码中使用：
```python
    # 此前错误：tokens = settings.GITHUB_TOKENS
    tokens = settings.github_token_list
    if not tokens:
        logger.error("No GITHUB_TOKENS configured.")
        return
        
    client = GitHubClient(tokens=tokens)
```

## 验证与预防
- 此项修复操作实施后，所有数据顺利拉取成功（返回 `200 OK`，配额消耗正常），并平稳推入 ClickHouse。
- **最佳实践建议**：往后如有新增的外部请求需求或微服务（如其它外行 API 数据源），请先行于主机或容器内依靠命令（`curl -I -x <proxy_url> <target_url>` 和 `curl -I --noproxy "*" <target_url>`）对其可用性对比探路，再决定是否下发布局内统一代理池策略。
