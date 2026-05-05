
import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Debug: Print env vars
print("-" * 50)
print("MySQL Connection Verification")
print("-" * 50)
print(f"Host: {os.getenv('GSD_DB_HOST')}")
print(f"Port: {os.getenv('GSD_DB_PORT')}")
print(f"User: {os.getenv('GSD_DB_USER')}")
print(f"DB:   {os.getenv('GSD_DB_NAME')}")
print("-" * 50)

async def verify_mysql():
    host = os.getenv('GSD_DB_HOST', 'localhost')
    port = os.getenv('GSD_DB_PORT', '3306')
    user = os.getenv('GSD_DB_USER', 'root')
    password = os.getenv('GSD_DB_PASSWORD', '')
    db = os.getenv('GSD_DB_NAME', 'stock_data')
    
    from urllib.parse import quote_plus
    encoded_user = quote_plus(user)
    encoded_password = quote_plus(password)
    
    dsn = f"mysql+aiomysql://{encoded_user}:{encoded_password}@{host}:{port}/{db}?charset=utf8mb4"
    
    print(f"Connecting to: mysql+aiomysql://{encoded_user}:****@{host}:{port}/{db}")
    
    try:
        engine = create_async_engine(dsn, echo=False)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"✅ Connection successful! Result: {result.scalar()}")
            
            # Try to list tables to prove read access
            result = await conn.execute(text("SHOW TABLES"))
            tables = result.fetchall()
            print(f"✅ Found {len(tables)} tables:")
            for table in tables[:5]:
                print(f"  - {table[0]}")
            if len(tables) > 5:
                print("  ... and more")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(verify_mysql())
    except KeyboardInterrupt:
        pass
