import asyncio
from app.core.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine

async def main():
    settings = get_settings()
    print("Connecting to:", settings.database_url)
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.connect() as conn:
            print("Successfully connected!")
    except Exception as e:
        print("Failed to connect:", repr(e))

if __name__ == "__main__":
    asyncio.run(main())
