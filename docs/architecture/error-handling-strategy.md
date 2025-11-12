# Error Handling Strategy

## Error Response Format
```typescript
interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
    timestamp: string;
    requestId: string;
  };
}
```

## Frontend Error Handling
```typescript
export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public details?: Record<string, any>
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export const handleApiError = (error: any): ApiError => {
  if (error.response?.data?.error) {
    const { code, message, details } = error.response.data.error;
    return new ApiError(code, message, details);
  }

  // 处理其他错误类型
  return new ApiError('UNKNOWN_ERROR', '未知错误');
};
```

## Backend Error Handling
```python
class BaseError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 400
    ):
        self.code = code
        self.message = message
        self.details = details
        self.status_code = status_code
        super().__init__(message)

def create_error_response(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 400
) -> JSONResponse:
    """创建标准错误响应"""
    error_response = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
            "requestId": str(uuid.uuid4())
        }
    }

    return JSONResponse(
        status_code=status_code,
        content=error_response
    )
```
