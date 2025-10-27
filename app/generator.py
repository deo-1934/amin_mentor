# app/generator.py
import requests
from app.settings import settings

def generate_answer(prompt: str) -> str:
    """
    Sends the prompt to the Hugging Face inference API and returns the generated text.
    """
    headers = {
        "Authorization": f"Bearer {settings.model_api_key}",
        "Content-Type": "application/json"
    }

    payload = {"inputs": prompt}

    try:
        response = requests.post(settings.model_endpoint, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        # بعضی مدل‌ها خروجی رو داخل لیست برمی‌گردونن
        if isinstance(data, list) and "generated_text" in data[0]:
            return data[0]["generated_text"]
        elif isinstance(data, dict) and "generated_text" in data:
            return data["generated_text"]
        else:
            return str(data)

    except Exception as e:
        return f"Error: {e}"
