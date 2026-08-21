import asyncio
from app.core.database import AsyncSessionLocal
from app.agents.discovery import GreenhouseDiscoveryAgent

async def run():
    agent = GreenhouseDiscoveryAgent('https://boards.greenhouse.io/anthropic')
    print("Discovering jobs...")
    jobs = await agent.discover_jobs()
    print(f"Discovered {len(jobs)} jobs. Saving to DB...")
    
    async with AsyncSessionLocal() as session:
        await agent.save_jobs(jobs, session)
        
    print("Saved to DB!")

if __name__ == "__main__":
    asyncio.run(run())
