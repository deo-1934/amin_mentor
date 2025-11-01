#FEYZ
#DEO
# -*- coding: utf-8 -*-
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

import requests

def _read_secret_or_env(key: str, default: str = "") -> str:
    try:
        import streamlit as st  # type: ignore
        if "secrets" in dir(st) and key in st.secrets:
            return str(st.secrets.get(key, default))
    except Exception:
        pass
    return os.environ.get(key, default)

def load_settings() -> Dict[str, Any]:
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    cache_path = data_dir / "cache.json"

    return {
        "MODEL_PROVIDER": _read_secret_or_env("MODEL_PROVIDER", "openai").strip().lower(),
        # OpenAI
        "OPENAI_API_KEY": _read_secret_or_env("OPENAI_API_KEY", ""),
        "OPENAI_MODEL": _read_secret_or_env("OPENAI_MODEL", "gpt-4o-mini"),
        # HF
        "MODEL_ENDPOINT": _read_secret_or_env("MODEL_ENDPOINT", "https://api-inference.huggingface.co/models/gpt2"),
        "HF_TOKEN": _read_secret_or_env("HF_TOKEN", ""),
        # misc
        "CACHE_PATH": str(cache_path),
        "HAS_SECRETS": True
    }

def _load_cache(path: str) -> Dict[str, Any]:
    try:
        if Path(path).exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_cache(path: str, data: Dict[str, Any]) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _format_for_ui(text: str) -> Dict[str, str]:
    text = (text or "").strip()
    if not text:
        return {"intro": "", "core": "", "outro": ""}

    lo = text.lower()
    if all(tag in lo for tag in ("<intro>", "</intro>", "<core>", "</core>", "<outro>", "</outro>")):
        def _extract(tag):
            s = lo.find(f"<{tag}>")
            e = lo.find(f"</{tag}>")
            if s != -1 and e != -1 and e > s:
                return text[s+len(tag)+2:e].strip()
            return ""
        return {"intro": _extract("intro"), "core": _extract("core"), "outro": _extract("outro")}

    n = len(text)
    a, b = int(n*0.2), int(n*0.8)
    return {"intro": text[:a].strip(), "core": text[a:b].strip(), "outro": text[b:].strip()}

#DEO
_RULES = [
    ("streamlit", "برای استقرار در Streamlit Cloud، runtime.txt با نسخهٔ 3.11، Secrets امن، و requirements پین‌شده لازم است."),
    ("faiss", "پاکسازی و تکه‌بندی متن، ساخت تعبیه با Sentence-Transformers، و ایندکس FAISS (IVFFLAT/HNSW) مسیر پیشنهادی است."),
    ("api", "ابتدا Rule-based و کش را فعال نگه‌دار، بعد سراغ مدل ابری برو تا هزینه کم شود."),
]

def _rule_based_answer(prompt: str) -> Optional[str]:
    p = (prompt or "").strip().lower()
    for k, ans in _RULES:
        if k in p:
            return ans
    return None

# ---- OpenAI ----
def _openai_generate(prompt: str, api_key: str, model: str, temperature: float, max_new_tokens: int, timeout: float = 30.0) -> str:
    if not api_key:
        raise ValueError("OPENAI_API_KEY تنظیم نشده است.")
    url = "https://api.openai.com/v1/responses"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "input": (
            "You are an expert Persian assistant for software/ML projects. "
            "Answer in Persian. Provide practical, concise guidance. "
            "Return plain text without markdown.\n\n"
            f"Question:\n{prompt}"
        ),
        "temperature": float(temperature),
        "max_output_tokens": int(max_new_tokens)
    }
    r = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"OpenAI API Error {r.status_code}: {r.text[:200]}")
    data = r.json()
    # new Responses API
    if "output_text" in data and isinstance(data["output_text"], str):
        return data["output_text"]
    # fallback older shapes
    if "choices" in data and data["choices"]:
        ch = data["choices"][0]
        if isinstance(ch, dict):
            return ch.get("message", {}).get("content") or ch.get("text") or ""
    return ""

# ---- HuggingFace ----
def _hf_generate(prompt: str, endpoint: str, token: str, temperature: float, max_new_tokens: int, timeout: float = 30.0) -> str:
    if not endpoint:
        raise ValueError("MODEL_ENDPOINT تنظیم نشده است.")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    payload = {
        "inputs": prompt,
        "parameters": {
            "temperature": float(temperature),
            "max_new_tokens": int(max_new_tokens),
            "return_full_text": False,
        }
    }
    r = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"HF API Error {r.status_code}: {r.text[:200]}")
    data = r.json()
    if isinstance(data, list) and data and isinstance(data[0], dict) and "generated_text" in data[0]:
        return str(data[0]["generated_text"])
    if isinstance(data, dict) and "generated_text" in data:
        return str(data["generated_text"])
    return json.dumps(data, ensure_ascii=False)

def generate_answer(
    query: str,
    model_provider: Optional[str] = None,
    # OpenAI
    openai_model: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    # HF
    model_endpoint: Optional[str] = None,
    hf_token: Optional[str] = None,
    # common
    temperature: float = 0.2,
    max_new_tokens: int = 256,
    top_k: int = 5,
) -> Dict[str, str]:
    cfg = load_settings()
    provider = (model_provider or cfg["MODEL_PROVIDER"]).strip().lower()
    # OpenAI
    oa_model = (openai_model or cfg.get("OPENAI_MODEL", "gpt-4o-mini")).strip()
    oa_key = (openai_api_key or cfg.get("OPENAI_API_KEY", "")).strip()
    # HF
    endpoint = (model_endpoint or cfg.get("MODEL_ENDPOINT", "")).strip()
    token = (hf_token or cfg.get("HF_TOKEN", "")).strip()

    cache_path = cfg["CACHE_PATH"]
    cache = _load_cache(cache_path)
    cache_key = json.dumps({"q": query.strip(), "prov": provider, "m": oa_model or endpoint, "t": round(temperature,2), "mx": int(max_new_tokens)}, ensure_ascii=False)
    rb = _rule_based_answer(query)
    if rb:
        return _format_for_ui(rb)
    if cache_key in cache:
        return cache[cache_key]

    if provider == "openai":
        try:
            text = _openai_generate(query, api_key=oa_key, model=oa_model, temperature=temperature, max_new_tokens=max_new_tokens)
            if not text.strip():
                text = "پاسخی از مدل دریافت نشد."
            result = _format_for_ui(text)
        except Exception as e:
            result = _format_for_ui(f"خطا در تماس با OpenAI: {e}")

    elif provider == "huggingface":
        try:
            prompt = (
                "You are an expert Persian assistant for software/ML projects. "
                "Answer in Persian, concise and practical. No markdown.\n\n"
                f"Question:\n{query}"
            )
            text = _hf_generate(prompt, endpoint=endpoint, token=token, temperature=temperature, max_new_tokens=max_new_tokens)
            if not text.strip():
                text = "پاسخی از مدل دریافت نشد."
            result = _format_for_ui(text)
        except Exception as e:
            result = _format_for_ui(f"خطا در تماس با HuggingFace: {e}")

    else:
        core = (
            f"سؤال: «{query.strip()}»\n\n"
            "پیشنهاد اجرایی سریع:\n"
            "1) مسئله را به یک قدم ۳۰-۶۰ دقیقه‌ای تبدیل کن.\n"
            "2) هر تغییر را با معیار «قابل‌نمایش در دمو» بسنج.\n"
            "3) برای کاهش هزینه، Rule-based و کش را قبل از تماس ابری فعال نگه‌دار."
        )
        result = {"intro": "یک مسیر کوتاه تا نتیجه ارائه می‌شود.", "core": core, "outro": "در صورت نیاز گام بعدی را دقیق‌تر تنظیم می‌کنم."}

    cache[cache_key] = result
    _save_cache(cache_path, cache)
    return result
