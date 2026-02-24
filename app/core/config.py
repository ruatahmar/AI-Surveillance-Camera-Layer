from pydantic import BaseSettings

class Settings(BaseSettings):
    class config:
        env_file: str = '.env'

settings = Settings()
