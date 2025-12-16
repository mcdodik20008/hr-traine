import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")  # Fallback для GigaChat
    GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID")  # Для OAuth2
    GIGACHAT_CLIENT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET")  # Для OAuth2
    GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY")  # Готовый base64 "client_id:secret"
    
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "hr_traine")
    # In Docker, use 'db' service name; locally use 'localhost'
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

    @property
    def DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

config = Config()
