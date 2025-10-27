# app/generator.py
import requests
from app.settings import settings

def generate_answer(prompt: str) -> str:
    """
    Sends the user prompt to the Hugging Face Inference API and returns the generated text.
    """
    try:
        headers = {
            "Authorization": f"Bearer {settings.hf_token}",
            "Content-Type": "application/json"
        }

        payload = {"inputs": prompt}

        response = requests.post(
            f"{settings.hf_endpoint}/{settings.hf_model}",
            headers=headers,
            json=payload
        )

        response.raise_for_status()
        result = response.json()

        if isinstance(result, list) and len(result) > 0:
            return result[0].get("generated_text", "")
        return str(result)

    except Exception as e:
        return f"Error: {e}"
