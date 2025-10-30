# app/settings.py
from pydantic_settings import BaseSettings
from pathlib import Path

# مسیرهای پایه پروژه
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
INDEX_DIR = BASE_DIR / "faiss_index"
INDEX_PATH = INDEX_DIR / "index.faiss"
META_PATH = INDEX_DIR / "meta.json"

# مدل امبدینگ پیش‌فرض برای FAISS
DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

class Settings(BaseSettings):
    # تنظیمات HuggingFace برای ژنراتور فعلی (اختیاری؛ بدون توکن هم پروژه بالا می‌آید)
    hf_token: str | None = None
    hf_model: str = "gpt2"
    hf_endpoint: str = "https://api-inference.huggingface.co/models"

    class Config:
        env_file = ".env"

settings = Settings()
