# app/deps.py
from functools import lru_cache
import os
from openai import OpenAI
from .retriever import Retriever

HF_BASE_URL = os.getenv("HF_BASE_URL", "https://router.huggingface.co/v1")
HF_API_KEY_ENV = "HUGGINGFACE_API_KEY"

@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    return Retriever()

@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    # OpenAI-compatible client pointing to Hugging Face Router
    api_key = os.getenv(HF_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(f"Missing {HF_API_KEY_ENV}. Set it in your shell before running the server.")
    return OpenAI(base_url=HF_BASE_URL, api_key=api_key)

def get_model_name(default: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"):
    # می‌توانی مدل را با ENV override کنی: OPENAI_MODEL
    return os.getenv("OPENAI_MODEL", default)
