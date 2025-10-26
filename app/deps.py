# app/deps.py
from functools import lru_cache
import os
from openai import OpenAI
from .retriever import Retriever

# Groq OpenAI-compatible endpoint
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_KEY_ENV = "GROQ_API_KEY"

@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    return Retriever()

@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    api_key = os.getenv(GROQ_KEY_ENV)
    if not api_key:
        raise RuntimeError(f"Missing {GROQ_KEY_ENV}. Set it before running the server.")
    return OpenAI(base_url=GROQ_BASE_URL, api_key=api_key)

def get_model_name(default: str = "llama-3.1-8b-instant"):
    # می‌تونی با ENV عوضش کنی: OPENAI_MODEL
    return os.getenv("OPENAI_MODEL", default)
