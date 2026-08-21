import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def get_count():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text('SELECT count(*) FROM job_postings;'))
        print('JOB COUNT:', res.scalar())

if __name__ == "__main__":
    asyncio.run(get_count())
