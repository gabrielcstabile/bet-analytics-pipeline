import asyncio
from src.extract.odds_api import get_sports

async def main():
    sports = await get_sports()
    for sport in sports:
        print(sport)

asyncio.run(main())