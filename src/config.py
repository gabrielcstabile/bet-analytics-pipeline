from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    odds_api_key: str
    odds_api_base_url: str = "https://api.the-odds-api.com/v4"
    
    model_config = {"env_file":".env"}
    
    
    
    
settings = Settings()