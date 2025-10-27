# app/generator.py
import os
import requests
from app.settings import settings

def generate(prompt: str) -> str:
    """
    Send a prompt to Hugging Face Inference API and return the generated text.
    """
    headers = {
        "Authorization": f"Bearer {settings.model_api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 200,
            "temperature": 0.7,
            "return_full_text": False
        }
    }

    try:
        response = requests.post(settings.model_endpoint, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return data[0]["generated_text"]
        else:
            return "⚠️ پاسخ مدل خالی بود یا ساختار نامعتبر داشت."
    except Exception as e:
        return f"❌ خطا در ارتباط با مدل: {e}"
