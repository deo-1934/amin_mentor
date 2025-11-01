#FEYZ
#DEO
# app/generator.py
from __future__ import annotations
import os
import json
import requests
from typing import List, Dict, Any

# ---- تنظیمات عمومی / ENV ----
MODEL_PROVIDER   = os.getenv("MODEL_PROVIDER", "huggingface").strip().lower()

# --- HuggingFace ---
MODEL_ENDPOINT   = os.getenv("MODEL_ENDPOINT", "https://api-inference.huggingface.co/models/gpt2").strip()
HF_TOKEN         = os.getenv("HF_TOKEN", "").strip()

# --- OpenAI ---
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL     = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

REQUEST_TIMEOUT  = float(os.getenv("REQUEST_TIMEOUT", "45"))

def healthcheck() -> Dict[str, Any]:
    return {
        "provider": MODEL_PROVIDER,
        "hf_endpoint": MODEL_ENDPOINT if MODEL_PROVIDER == "huggingface" else None,
        "openai_model": OPENAI_MODEL if MODEL_PROVIDER == "openai" else None,
    }

# ---------- سازندهٔ پرامپت هیبرید ----------
def _build_hybrid_prompt(user_question: str, context_chunks: List[str]) -> str:
    ctx = "\n\n".join(f"[منبع {i+1}]\n{t}" for i, t in enumerate(context_chunks))
    prompt = (
        "شما یک منتور عملی و دقیق هستید. با تکیه بر منابع زیر، پاسخ کوتاه، شفاف و اجرایی بده.\n"
        "اگر پاسخ در منابع نبود، صادقانه بگو «در منابع موجود نیست» و یک مسیر اقدام پیشنهاد بده.\n\n"
        f"[زمینه]\n{ctx}\n\n"
        f"[سوال کاربر]\n{user_question}\n\n"
        "[پاسخ]\n"
    )
    return prompt

# ---------- کالِر HuggingFace ----------
def _call_hf(prompt: str, max_new_tokens: int) -> str:
    if not MODEL_ENDPOINT or not HF_TOKEN:
        raise RuntimeError("HF endpoint/token is not configured.")
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": max_new_tokens, "temperature": 0.7},
    }
    r = requests.post(MODE_ENDPOINT, headers=headers, data=json.dumps(payload), timeout=REQUEST_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"HF API error: {r.status_code} {r.text[:300]}")
    data = r.json()
    if isinstance(data, list) and data and "generated_text" in data[0]:
        return data[0]["generated_text"]
    if isinstance(data, dict) and "generated_text" in data:
        return data["generated_text"]
    # fallback
    return json.dumps(data)[:2000]

# ---------- کالِر OpenAI (Chat Completions) ----------
def _call_openai(prompt: str, max_new_tokens: int) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY.")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": "You are a concise, actionable Persian mentor."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_new_tokens,
        "temperature": 0.7,
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=REQUEST_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"OpenAI API error: {r.status_code} {r.text[:300]}")
    data = r.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        return json.dumps(data)[:2000]

# ---------- اینترفیس اصلی ----------
def generate_answer(user_question: str, context: List[str], max_new_tokens: int = 256) -> str:
    prompt = _build_hybrid_prompt(user_question=user_question, context_chunks=context)
    if MODEL_PROVIDER == "openai":
        answer = _call_openai(prompt, max_new_tokens=max_new_tokens)
    elif MODEL_PROVIDER == "huggingface":
        answer = _call_hf(prompt, max_new_tokens=max_new_tokens)
    else:
        raise RuntimeError(f"Unsupported MODEL_PROVIDER: {MODEL_PROVIDER}")

    # حذف echo احتمالی
    tail_split_marker = "[سوال کاربر]"
    if tail_split_marker in answer:
        answer = answer.split(tail_split_marker)[-1].strip()
    return answer.strip()
#FEYZ
#DEO
