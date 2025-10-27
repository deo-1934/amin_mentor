# app/settings.py
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_endpoint: str = os.getenv("MODEL_ENDPOINT", "https://api-inference.huggingface.co/models/gpt2")
    model_api_key: str = os.getenv("MODEL_API_KEY", "")
    model_provider: str = os.getenv("MODEL_PROVIDER", "huggingface")
    streaming: bool = os.getenv("STREAMING", "false").lower() == "true"

settings = Settings()
