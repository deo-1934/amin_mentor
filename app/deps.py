# app/deps.py
from functools import lru_cache
import os
from openai import OpenAI
from .retriever import Retriever

# ----------------------------
# OpenAI (ChatGPT) configuration
# ----------------------------
# - کلید: از ENV به نام OPENAI_API_KEY
# - مدل پیش‌فرض: gpt-4o-mini (قابل تغییر با OPENAI_MODEL)

@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    return Retriever()

@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    # اگر OPENAI_API_KEY ست نباشه، SDK خودش خطای واضح می‌ده
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY. Set it before running the server.")
    return OpenAI(api_key=api_key)

def get_model_name(default: str = "gpt-4o-mini") -> str:
    return os.getenv("OPENAI_MODEL", default)
