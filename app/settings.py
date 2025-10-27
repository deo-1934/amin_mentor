from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    hf_token: str
    hf_model: str = "gpt2"
    hf_endpoint: str = "https://api-inference.huggingface.co/models"

    class Config:
        env_file = ".env"

settings = Settings()
