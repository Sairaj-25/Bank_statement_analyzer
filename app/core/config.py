from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    MAX_FILE_SIZE_MB: int = 10
    TEMP_DIR: str = "temp_uploads"
    EXPORT_DIR: str = "exports"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        os.makedirs(self.TEMP_DIR, exist_ok=True)
        os.makedirs(self.EXPORT_DIR, exist_ok=True)

settings = Settings()