import httpx
from src.config import settings
from src.models.odds_api import Sport

async def get_sports() -> list[Sport]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.odds_api_base_url}/sports",
            params={"apiKey": settings.odds_api_key},
        )
        
        response.raise_for_status()
        data = response.json()        
        
        list_sport = []
        
        for item in data:
            list_sport.append(Sport(**item))
        
    return list_sport