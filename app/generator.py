#FEYZ
#DEO
# -*- coding: utf-8 -*-
"""
generator.py
- خروجی: یک متن یک‌تکه (string)
- اتصال به OpenAI وقتی MODEL_PROVIDER="openai"
- اتصال به HuggingFace وقتی MODEL_PROVIDER="huggingface"
- کش برای کاهش هزینه
"""

import os, json
from pathlib import Path
from typing import Dict, Any, Optional, List
import requests

try:
    from openai import OpenAI  # SDK جدید OpenAI
except Exception:
    OpenAI = None


def _read_secret_or_env(key: str, default: str = "") -> str:
    # اول از st.secrets بخون (Streamlit Cloud)، بعد از env لوکال
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


def _join_context(context: Optional[List[str]]) -> str:
    if not context:
        return ""
    cleaned = [c.strip() for c in context if c and c.strip()]
    if not cleaned:
        return ""
    ctx = "\n\n".join(cleaned)
    return (
        "\n\n[دانش داخلی مرتبط برای کمک به کیفیت پاسخ. این بخش برای مدل است و مستقیم به کاربر نشان داده نمی‌شود:]\n"
        f"{ctx}\n"
    )


_RULES = {
    "streamlit": (
        "برای استقرار پایدار روی Streamlit Cloud از runtime.txt با نسخهٔ پایتون ثابت استفاده کن، "
        "Secrets را جایگزین .env کن و با اضافه کردن __init__.py در پوشهٔ app از خطای ModuleNotFoundError جلوگیری کن."
    ),
    "faiss": (
        "برای جست‌وجوی دانش لوکال سریع، متن‌ را تمیز و تکه‌بندی کن، با all-MiniLM-L6-v2 امبدینگ بگیر "
        "و نتایج را در FAISS ایندکس کن تا top_k سریع بازیابی شود."
    ),
    "api": (
        "برای کاهش هزینهٔ API، سؤالات تکراری را کش کن و فقط وقتی واقعاً لازم شد سراغ مدل ابری برو. "
        "هر سؤال جدید را اول به یک قدم کوچک و قابل‌اجرا تبدیل کن."
    ),
    "کسب و کار": (
        "اول مشکل واقعی مشتری را دقیق بفهم. بدون درک نیاز واقعی، رشد فقط توهمه. "
        "ارزش ملموس بده، بعد مقیاس‌پذیری را حل کن."
    ),
    "مذاکره": (
        "در مذاکره گوش دادن از حرف زدن مهم‌تر است. اول بفهم طرف مقابل دقیقاً چه دردی دارد و چرا. "
        "هدف قانع کردن زورکی نیست؛ هدف رسیدن به نقطهٔ برد-برد است."
    ),
}


def _rule_based_answer(query: str) -> Optional[str]:
    q_low = (query or "").lower()
    for key, val in _RULES.items():
        if key.lower() in q_low:
            return val
    return None


def _hf_generate(prompt: str,
                 endpoint: str,
                 token: str,
                 temperature: float,
                 max_new_tokens: int,
                 timeout: float = 40.0) -> str:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    payload = {
        "inputs": prompt,
        "parameters": {
            "temperature": float(temperature),
            "max_new_tokens": int(max_new_tokens),
            "return_full_text": False,
        },
    }
    r = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()

    if isinstance(data, list) and data and isinstance(data[0], dict) and "generated_text" in data[0]:
        return str(data[0]["generated_text"]).strip()
    if isinstance(data, dict) and "generated_text" in data:
        return str(data["generated_text"]).strip()

    return json.dumps(data, ensure_ascii=False)


#DEO
def _openai_generate(prompt: str,
                     api_key: str,
                     model_name: str,
                     temperature: float,
                     max_new_tokens: int) -> str:
    if not OpenAI:
        raise RuntimeError("openai package not available")

    client = OpenAI(api_key=api_key)

    # در SDK جدید، مدل‌های سری gpt-4o با responses.create صدا زده می‌شن.
    response = client.responses.create(
        model=model_name,
        input=prompt,
        temperature=float(temperature),
        max_output_tokens=int(max_new_tokens),
    )

    text_out = None

    # حالت جدید: response.output (لیست آیتم‌ها با segmentهای متنی)
    try:
        if hasattr(response, "output") and response.output:
            parts = []
            for item in response.output:
                # item ممکنه .content (لیست) یا .text داشته باشه
                if hasattr(item, "content") and item.content:
                    segs = []
                    for seg in item.content:
                        if hasattr(seg, "text") and seg.text:
                            segs.append(seg.text)
                    if segs:
                        parts.append("\n".join(segs))
                elif hasattr(item, "text") and item.text:
                    parts.append(item.text)
            if parts:
                text_out = "\n".join(parts).strip()
    except Exception:
        pass

    # حالت قدیمی‌تر / fallback
    if (not text_out) and hasattr(response, "output_text"):
        try:
            text_out = str(response.output_text).strip()
        except Exception:
            pass

    if (not text_out) and hasattr(response, "choices"):
        try:
            if response.choices and hasattr(response.choices[0], "message"):
                msg = response.choices[0].message
                if hasattr(msg, "content"):
                    text_out = str(msg.content).strip()
        except Exception:
            pass

    if not text_out:
        text_out = str(response)

    return text_out


def healthcheck() -> Dict[str, Any]:
    s = load_settings()
    return {
        "provider": s["MODEL_PROVIDER"],
        "has_openai_key": bool(s["OPENAI_API_KEY"]),
        "openai_model": s["OPENAI_MODEL"],
        "has_hf_token": bool(s["HF_TOKEN"]),
    }


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
    فقط یک متن نهایی و یکپارچه برمی‌گرداند.
    """

    s = load_settings()

    provider = (model_provider or s["MODEL_PROVIDER"]).lower()
    temperature = float(temperature if temperature is not None else s["DEFAULT_TEMPERATURE"])
    max_new_tokens = int(max_new_tokens if max_new_tokens is not None else s["DEFAULT_MAX_NEW_TOKENS"])

    api_key = openai_api_key or s["OPENAI_API_KEY"]
    model_name = openai_model or s["OPENAI_MODEL"]
    endpoint = model_endpoint or s["MODEL_ENDPOINT"]
    hf_tok = hf_token or s["HF_TOKEN"]

    cache_path = s["CACHE_PATH"]
    cache = _load_cache(cache_path)

    ctx_block = _join_context(context)
    prompt = (
        "شما یک منتور فارسی هستی. پاسخ باید شفاف، محترمانه و عملی باشد. "
        "پاسخ را فقط در قالب یک متن یک‌تکه بده. هیچ بخش‌بندی رسمی (مقدمه، جمع‌بندی و...) نده.\n\n"
        f"سؤال کاربر:\n{query.strip()}\n"
        f"{ctx_block}"
    )

    cache_key = f"{provider}:{hash((query, ctx_block, max_new_tokens, temperature))}"
    if cache_key in cache:
        return str(cache[cache_key])

    rb = _rule_based_answer(query)
    if rb:
        cache[cache_key] = rb
        _save_cache(cache_path, cache)
        return rb

    if provider == "openai" and api_key:
        try:
            text = _openai_generate(
                prompt=prompt,
                api_key=api_key,
                model_name=model_name,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
            )
            cache[cache_key] = text
            _save_cache(cache_path, cache)
            return text
        except Exception:
            pass

    if provider == "huggingface" and hf_tok:
        try:
            text = _hf_generate(
                prompt=prompt,
                endpoint=endpoint,
                token=hf_tok,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
            )
            cache[cache_key] = text
            _save_cache(cache_path, cache)
            return text
        except Exception:
            pass

    fallback_text = (
        "برای رسیدن سریع به نتیجه، مسئله‌ات را به یک گام ۳۰ تا ۶۰ دقیقه‌ای تبدیل کن و فقط همان گام را انجام بده. "
        "هر تغییری را با این سؤال بسنج: «آیا می‌توانم همین امروز نشانش بدهم؟» "
        "از تکرار کار جلوگیری کن و فقط وقتی لازم شد سراغ مدل ابری برو تا هزینه پایین بماند."
    )

    cache[cache_key] = fallback_text
    _save_cache(cache_path, cache)
    return fallback_text
