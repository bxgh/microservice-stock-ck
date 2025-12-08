import asyncio
import sys
import os

# Ensure src is in path
sys.path.insert(0, "/app")

from src.storage.rdbms.database import db
from src.config.settings import settings

async def main():
    print(f"DEBUG: CWD = {os.getcwd()}")
    print(f"DEBUG: .env exists? {os.path.exists('.env')}")
    print(f"DEBUG: database_type = {settings.database_type}")
    print(f"DEBUG: database_url = {settings.database_url}")
    
    print("Initializing database tables...")
    try:
        await db.create_tables()
        print("✅ Database tables created successfully.")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
