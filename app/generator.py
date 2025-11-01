#FEYZ
#DEO
# -*- coding: utf-8 -*-
import os, json
from pathlib import Path
from typing import Dict, Any, Optional, List
import requests

def _read_secret_or_env(key: str, default: str = "") -> str:
    try:
        import streamlit as st  # type: ignore
        if key in getattr(st, "secrets", {}):
            return str(st.secrets.get(key, default))
    except Exception:
        pass
    return os.getenv(key, default)

def load_settings() -> Dict[str, Any]:
    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    cache_path = data_dir / "cache.json"
    return {
        "MODEL_PROVIDER": _read_secret_or_env("MODEL_PROVIDER", "openai").strip().lower(),
        "OPENAI_API_KEY": _read_secret_or_env("OPENAI_API_KEY", ""),
        "OPENAI_MODEL": _read_secret_or_env("OPENAI_MODEL", "gpt-4o-mini"),
        "MODEL_ENDPOINT": _read_secret_or_env("MODEL_ENDPOINT", "https://api-inference.huggingface.co/models/gpt2"),
        "HF_TOKEN": _read_secret_or_env("HF_TOKEN", ""),
        "CACHE_PATH": str(cache_path),
        "DEFAULT_MAX_NEW_TOKENS": int(_read_secret_or_env("MAX_NEW_TOKENS", "256")),
        "DEFAULT_TEMPERATURE": float(_read_secret_or_env("TEMPERATURE", "0.2")),
    }

#DEO
def _load_cache(path: str) -> Dict[str, Any]:
    try:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _save_cache(path: str, data: Dict[str, Any]) -> None:
    try:
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

_RULES = {
    "streamlit": "برای استقرار پایدار در Streamlit Cloud از Python 3.11، فایل runtime.txt، Secrets امن و requirements پین‌شده استفاده کن. برای خطای ماژول، __init__.py و import نسبی را اصلاح کن.",
    "faiss": "برای جست‌وجوی سریع: پاکسازی متن، تکه‌بندی منطقی، تعبیه با all-MiniLM-L6-v2 و ایندکس FAISS. meta.json را کنار index.faiss ذخیره کن تا منبع هر قطعه مشخص باشد.",
    "api": "برای کاهش هزینهٔ API، اول حالت Rule-based و کش نتایج را فعال کن؛ سپس برای پرسش‌های جدید سراغ مدل ابری برو.",
}

def _rule_based_answer(query: str) -> Optional[str]:
    p = (query or "").lower()
    for k, ans in _RULES.items():
        if k in p:
            return ans
    return None

def _hf_generate(prompt: str, endpoint: str, token: str, temperature: float, max_new_tokens: int, timeout: float = 40.0) -> str:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    payload = {"inputs": prompt, "parameters": {"temperature": float(temperature), "max_new_tokens": int(max_new_tokens), "return_full_text": False}}
    r = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list) and data and isinstance(data[0], dict) and "generated_text" in data[0]:
        return str(data[0]["generated_text"]).strip()
    if isinstance(data, dict) and "generated_text" in data:
        return str(data["generated_text"]).strip()
    return json.dumps(data, ensure_ascii=False)

def _join_context(context: Optional[List[str]]) -> str:
    if not context:
        return ""
    ctx = "\n".join([c.strip() for c in context if c and c.strip()])
    return f"\n\n[زمینه]\n{ctx}\n"

def healthcheck() -> Dict[str, Any]:
    s = load_settings()
    return {"provider": s["MODEL_PROVIDER"], "has_openai_key": bool(s["OPENAI_API_KEY"]), "has_hf_token": bool(s["HF_TOKEN"])}

def generate_answer(
    query: str,
    *,
    model_provider: Optional[str] = None,
    openai_model: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    model_endpoint: Optional[str] = None,
    hf_token: Optional[str] = None,
    temperature: Optional[float] = None,
    max_new_tokens: Optional[int] = None,
    top_k: int = 5,
    context: Optional[List[str]] = None,
) -> str:
    """
    خروجی: یک رشتهٔ یکپارچه (بدون مقدمه/هسته/جمع‌بندی جداگانه).
    """
    s = load_settings()
    provider = (model_provider or s["MODEL_PROVIDER"]).lower()
    temperature = float(temperature if temperature is not None else s["DEFAULT_TEMPERATURE"])
    max_new_tokens = int(max_new_tokens if max_new_tokens is not None else s["DEFAULT_MAX_NEW_TOKENS"])
    cache_path = s["CACHE_PATH"]
    cache = _load_cache(cache_path)

    ctx_block = _join_context(context)
    prompt = (
        f"پرسش کاربر: {query.strip()}\n"
        f"الزام: پاسخ را یکپارچه، دقیق، کوتاه‌نویسی‌شده و کاربردی بده. از بخش‌بندی صوری پرهیز کن.{ctx_block}"
    )

    cache_key = f"{provider}:{hash((query, ctx_block, max_new_tokens, temperature))}"
    if cache_key in cache:
        return str(cache[cache_key])

    rb = _rule_based_answer(query)
    if rb:
        text = rb
    elif provider == "huggingface":
        text = _hf_generate(prompt, model_endpoint or s["MODEL_ENDPOINT"], hf_token or s["HF_TOKEN"], temperature, max_new_tokens)
    else:
        text = (
            "برای رسیدن سریع به نتیجه: مسئله را به یک گام ۳۰–۶۰ دقیقه‌ای تبدیل کن، "
            "هر تغییر را با معیار «قابل‌نمایش در دمو» بسنج و تا حد امکان از کش استفاده کن؛ "
            "سپس برای پرسش‌های جدید سراغ مدل ابری برو."
        )

    cache[cache_key] = text
    _save_cache(cache_path, cache)
    return text
