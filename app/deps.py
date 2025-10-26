# app/deps.py
from functools import lru_cache
import os
from typing import Optional
from openai import OpenAI
from .retriever import Retriever

@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    return Retriever()

@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    # از OPENAI_API_KEY در محیط استفاده می‌کند
    return OpenAI()

def get_model_name(default: str = "gpt-4o-mini") -> str:
    return os.getenv("OPENAI_MODEL", default)
