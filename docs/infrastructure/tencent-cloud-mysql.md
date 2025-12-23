# Tencent Cloud MySQL Configuration

## Connection Details

**Database Type**: MySQL 5.7+ (Tencent Cloud CDB)

### Connection Parameters

```python
DB_CONFIG = {
    'host': 'sh-cdb-h7flpxu4.sql.tencentcdb.com',  # Shanghai region
    'port': 26300,
    'database': 'alwaysup',
    'user': 'root',
    'charset': 'utf8mb4'
}
```

### Environment Variables

```bash
MYSQL_HOST=sh-cdb-h7flpxu4.sql.tencentcdb.com
MYSQL_PORT=26300
MYSQL_DATABASE=alwaysup
MYSQL_USER=root
MYSQL_PASSWORD=alwaysup@888
```

### Network Access

- **Internal Access**: Available from Tencent Cloud VPC
- **External Access**: Through internal proxy `http://192.168.151.18:3128`
- **Region**: Shanghai (sh)

### Usage in Services

This MySQL instance is configured in:
- `services/task-scheduler/.env`
- `services/stock-data/.env`

### Purpose

- **Primary Role**: Cloud backup storage for financial data
- **Data Sync**: Receives dual-write data from `data-collector`
- **Use Cases**: 
  - Disaster recovery
  - Historical data archival
  - Financial statements storage
  - K-line historical data

### Security Notes

⚠️ **IMPORTANT**: 
- Credentials are stored in `.env` files (gitignored)
- Never commit credentials to version control
- Use environment variables in production
- Rotate passwords regularly

### Connection Example

```python
import aiomysql

async def get_connection():
    conn = await aiomysql.connect(
        host='sh-cdb-h7flpxu4.sql.tencentcdb.com',
        port=26300,
        user='root',
        password='alwaysup@888',
        db='alwaysup',
        charset='utf8mb4'
    )
    return conn
```

### Related Resources

- Tencent Cloud Server: `124.221.80.250`
- AkShare API: `http://124.221.80.250:8003`
- Baostock API: `http://124.221.80.250:8001`
- Pywencai API: `http://124.221.80.250:8002`

---
*Last Updated: 2025-12-24*
*Configuration Status: Active*
