from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    
    APP_NAME: str
    APP_VERSION: str
    APP_DESCRIPTION: str
    FILE_ALLOWED_EXTENTIONS: list
    FILE_MAX_SIZE_IN_MB: int
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
def get_settings() -> Settings:
    return Settings()