import asyncio
import aiomysql
import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings

async def apply_migrations():
    """Apply all SQL migrations in order"""
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    sql_files = sorted(list(migrations_dir.glob("*.sql")))
    
    pool = await aiomysql.create_pool(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        db=settings.MYSQL_DATABASE,
        minsize=1,
        maxsize=5
    )

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Create history table
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS `alwaysup`.`migrations_history` (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    migration_name VARCHAR(255) UNIQUE NOT NULL,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            for migration_file in sql_files:
                migration_name = migration_file.name
                
                # Check history
                await cursor.execute(
                    "SELECT id FROM alwaysup.migrations_history WHERE migration_name = %s",
                    (migration_name,)
                )
                if await cursor.fetchone():
                    print(f"Skipping {migration_name} (already applied)")
                    continue
                
                print(f"Applying {migration_name}...")
                with open(migration_file, 'r') as f:
                    content = f.read()
                
                statements = [s.strip() for s in content.split(';') if s.strip()]
                for stmt in statements:
                    await cursor.execute(stmt)
                
                await cursor.execute(
                    "INSERT INTO alwaysup.migrations_history (migration_name) VALUES (%s)",
                    (migration_name,)
                )
                await conn.commit()
                print(f"✅ Applied {migration_name}")

    pool.close()
    await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(apply_migrations())
