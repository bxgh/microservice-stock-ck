
import asyncio
from adapters.clickhouse_loader import ClickHouseLoader

async def inspect_db():
    loader = ClickHouseLoader()
    await loader.initialize()
    try:
        # 查看所有数据库
        print("Databases:")
        dbs = loader.client.execute("SHOW DATABASES")
        for db in dbs:
            print(f"- {db[0]}")
            
        # 查看当前数据库的所有表
        current_db = loader.client.execute("SELECT currentDatabase()")[0][0]
        print(f"\nTables in '{current_db}':")
        tables = loader.client.execute("SHOW TABLES")
        for table in tables:
            print(f"- {table[0]}")
            
        # 如果有 quotes 数据库，也看看
        if ('quotes',) in dbs:
            print(f"\nTables in 'quotes':")
            tables_q = loader.client.execute("SHOW TABLES FROM quotes")
            for table in tables_q:
                print(f"- {table[0]}")
                
    finally:
        await loader.close()

if __name__ == "__main__":
    asyncio.run(inspect_db())
