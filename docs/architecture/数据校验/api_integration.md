# 接口集成标准 (API Integration Standards)

为确保微服务间通信的健壮性，本项目采用统一的响应契约与智能客户端模式。

## 1. 核心组件

所有基础组件位于 `gsd-shared` 库中：

- **`gsd_shared.models.api`**: 定义统一的请求/响应模型。
- **`gsd_shared.api_client`**: 提供集成校验能力的 HTTP 客户端基类。
- **`gsd_shared.exceptions`**: 定义标准契约异常。

## 2. 响应契约 (Response Contract)

### 2.1 统一外壳 (Envelope)

所有内部 API **必须** 返回以下 JSON 结构：

```json
{
  "code": 200,
  "message": "success",
  "data": { ... },   // 业务数据
  "success": true
}
```

对应 Pydantic 模型：`ApiResponse[T]`

### 2.2 定义业务模型

在 `gsd_shared.models.api` 中定义具体的 `data` 结构。

```python
from pydantic import BaseModel
from gsd_shared.models.api.response import ApiResponse

# 1. 定义业务数据模型
class UserInfo(BaseModel):
    id: int
    name: str

# 2. 定义完整的响应类型 (用于类型提示)
UserResponse = ApiResponse[UserInfo]
```

## 3. 客户端开发 (Client Development)

不建议直接使用 `httpx` 或 `requests`。应继承 `BaseApiClient` 以获得自动校验能力。

### 3.1 实现 Client

```python
from gsd_shared.api_client import BaseApiClient
from gsd_shared.models.api.response import ApiResponse

class UserClient(BaseApiClient):
    
    async def get_user(self, user_id: int) -> UserInfo:
        """
        调用 /users/{id}
        
        自动校验：
        1. HTTP 状态码
        2. JSON 结构 (code/msg/data)
        3. 业务数据模型 (UserInfo)
        """
        return await self.get_object(
            endpoint=f"/users/{user_id}",
            response_model=ApiResponse[UserInfo]  # 指定泛型供校验
        )
```

### 3.2 调用 Client

```python
client = UserClient(base_url="http://user-service")

try:
    user = await client.get_user(1001)
    print(f"User: {user.name}")
    
except SchemaValidationError as e:
    # 契约不仅包含 HTTP 200，还包含 JSON 结构正确
    logger.error(f"接口返回数据异常: {e}")
    
except httpx.HTTPError as e:
    # 网络错误或非 200 响应
    logger.error(f"网络请求失败: {e}")
    
finally:
    await client.close()
```

## 4. 异常处理

| 异常类型 | 触发场景 | 处理建议 |
| :--- | :--- | :--- |
| `httpx.HTTPStatusError` | HTTP 4xx/5xx 或 `code != 200` | 视为调用失败，可重试 |
| `SchemaValidationError` | 响应 JSON 无法通过 Pydantic 校验 | **严重错误**，上游服务变更契约，需人工介入 |
| `httpx.TimeoutException`| 请求超时 | 视为暂时不可用，可重试 |

## 5. 最佳实践

1. **Schema First**: 先更新 `gsd-shared` 中的 Model，再开发服务端接口和客户端代码。
2. **Fail Fast**: 遇到 `SchemaValidationError` 应立即报错，不要尝试"尽力解析"，避免脏数据进入系统。
3. **Type Hinting**: 利用 Pydantic 的泛型支持，确保 IDE 能正确提示 `data` 内部的字段。
