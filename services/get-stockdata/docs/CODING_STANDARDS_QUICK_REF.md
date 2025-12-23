# 编程规范速查表

## 🚫 绝对禁止

| 禁止项 | 正确做法 |
|--------|----------|
| `PROXY_URL=http://127.0.0.1:8118` | `PROXY_URL=http://192.168.151.18:3128` |
| `import akshare as ak` | `from data_sources.providers.akshare_provider import AkshareProvider` |
| `import baostock as bs` | `from data_sources.providers.baostock_provider import BaostockProvider` |
| Fallback 到本地库 | 直接 `raise` 错误 |
| 返回 Mock 数据 | 返回错误或空结果 |

## ✅ 必须遵守

1. **云端 API 地址** (写死，不可变):
   ```python
   AKSHARE_API_URL = "http://124.221.80.250:8003"
   BAOSTOCK_API_URL = "http://124.221.80.250:8001"
   PROXY_URL = "http://192.168.151.18:3128"
   ```

2. **错误处理** - Fail-Fast:
   ```python
   # ✅ 正确
   try:
       data = await cloud_api.fetch()
   except Exception as e:
       logger.error(f"Cloud API failed: {e}")
       raise  # 直接抛出
   
   # ❌ 错误 - 禁止 fallback
   except Exception:
       import akshare as ak
       return ak.stock_financial_abstract()
   ```

3. **唯一本地数据源**: Mootdx (TCP 直连)
   ```python
   from data_sources.providers.mootdx_provider import MootdxProvider
   ```

## 📖 完整规范

详见: [`docs/CODING_STANDARDS.md`](CODING_STANDARDS.md)
