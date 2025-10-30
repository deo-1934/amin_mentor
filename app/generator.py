"""
app/generator.py
مولد پاسخ واحد پروژه.
- تابع عمومی: generate_answer(prompt: str, context: list[str] | None = None) -> str
- اگر متغیرهای محیطی Hugging Face تنظیم باشد، از endpoint هاگینگ‌فیس استفاده می‌کند.
- اگر تنظیم نباشد یا خطایی رخ دهد، یک پاسخ ایمن (fallback) برمی‌گرداند تا سیستم از کار نیفتد.
"""

from __future__ import annotations

import os
import json
import logging
from typing import List, Optional, Dict, Any
import requests

# --- لاگینگ سبک و کاربردی ---
logger = logging.getLogger("generator")
if not logger.handlers:
    handler = logging.StreamHandler()
    fmt = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# --- پیکربندی از env با مقادیر پیش‌فرض امن ---
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "huggingface").strip().lower()
MODEL_ENDPOINT = os.getenv(
    "MODEL_ENDPOINT",
    # نمونهٔ پیش‌فرض عمومی (الزامی نیست که در همه مدل‌ها کار کند؛ صرفاً الگو)
    "https://api-inference.huggingface.co/models/gpt2"
).strip()
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
REQUEST_TIMEOUT = float(os.getenv("GENERATOR_TIMEOUT_SECS", "30"))  # ثانیه
MAX_NEW_TOKENS_DEFAULT = int(os.getenv("MAX_NEW_TOKENS", "200"))


def _join_context(context: Optional[List[str]]) -> str:
    if not context:
        return ""
    # خلاصه‌سازیِ سادهٔ کانتکست برای ارسال به مدل (از تکرار طولانی جلوگیری می‌شود)
    # ترجیحاً در آینده با summarizer جایگزین شود.
    joined = "\n\n".join([c.strip() for c in context if c and c.strip()])
    # محدودیت نرم 2000 کاراکتر برای payload
    if len(joined) > 2000:
        joined = joined[:2000] + " …"
    return joined


def _build_prompt(prompt: str, context: Optional[List[str]]) -> str:
    ctx = _join_context(context)
    if ctx:
        return f"""System: You are a helpful assistant. Use the provided context when relevant.
Context:
{ctx}

User: {prompt}
Assistant:"""
    else:
        return prompt


def _hf_headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"
    return headers


def _hf_payload(text: str, max_new_tokens: int) -> Dict[str, Any]:
    # پارامترها برای text-generation. بعضی مدل‌ها ساختار متفاوت دارند؛
    # این مجموعه روی اکثر endpointهای هاگینگ‌فیس جواب می‌دهد.
    return {
        "inputs": text,
        "parameters": {
            "max_new_tokens": max_new_tokens,
            "temperature": 0.7,
            "top_p": 0.95,
            "do_sample": True,
            # اگر مدل chat باشد، معمولاً نادیده گرفته می‌شود.
            # اینجا با کمترین فرض ممکن جلو می‌رویم.
        },
        "options": {
            "wait_for_model": True
        }
    }


def _extract_hf_text(resp_json: Any, original_prompt: str) -> str:
    """
    خروجی API هاگینگ‌فیس ممکن است اشکال مختلفی داشته باشد:
    - [{'generated_text': '...'}]
    - {'generated_text': '...'}
    - مدل‌های chat ممکن است لیست پاسخ‌ها را متفاوت بدهند.
    سعی می‌کنیم متن را با بهترین تلاش استخراج کنیم.
    """
    try:
        if isinstance(resp_json, list) and resp_json:
            item0 = resp_json[0]
            if isinstance(item0, dict):
                if "generated_text" in item0:
                    return str(item0["generated_text"])
                # برخی مدل‌ها 'translation_text' یا کل متن را در 'generated_text' قرار نمی‌دهند
                # در این صورت همهٔ dict را به رشته تبدیل می‌کنیم.
                return json.dumps(item0, ensure_ascii=False)
        if isinstance(resp_json, dict):
            if "generated_text" in resp_json:
                return str(resp_json["generated_text"])
            # پیام خطای مدل یا ساختار سفارشی
            if "error" in resp_json:
                return f"[HF error] {resp_json['error']}"
            return json.dumps(resp_json, ensure_ascii=False)
    except Exception as e:
        logger.warning("failed to parse HF response: %s", e)

    # اگر هیچ‌کدام نگرفت:
    return f"(no structured generated_text; raw) {json.dumps(resp_json, ensure_ascii=False)[:1000]}"


def _call_huggingface_inference(text: str, max_new_tokens: int) -> str:
    if not MODEL_ENDPOINT:
        raise RuntimeError("MODEL_ENDPOINT تنظیم نشده است.")
    url = MODEL_ENDPOINT

    headers = _hf_headers()
    payload = _hf_payload(text, max_new_tokens)

    logger.info("Calling HF inference: %s", url)
    r = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return _extract_hf_text(r.json(), text)


def generate_answer(
    prompt: str,
    context: Optional[List[str]] = None,
    max_new_tokens: int = MAX_NEW_TOKENS_DEFAULT
) -> str:
    """
    نقطهٔ ورود واحد برای تولید پاسخ.
    - در حالت ایده‌آل از هاگینگ‌فیس استفاده می‌کند.
    - اگر توکن/اندپوینت نبود یا اروری رخ داد، پاسخ fallback می‌دهد تا مسیر RAG از کار نیفتد.
    """
    prompt = (prompt or "").strip()
    if not prompt:
        return "⚠️ ورودی خالی است."

    built = _build_prompt(prompt, context)

    if MODEL_PROVIDER == "huggingface":
        # تلاش برای تماس واقعی با HF
        if MODEL_ENDPOINT and HF_TOKEN:
            try:
                text = _call_huggingface_inference(built, max_new_tokens=max_new_tokens)
                # بعضی مدل‌ها کل prompt + completion را برمی‌گردانند؛ فقط بخش پس از "Assistant:" را جدا می‌کنیم.
                if "Assistant:" in text:
                    text = text.split("Assistant:", 1)[-1].strip()
                return text.strip()
            except Exception as e:
                logger.error("HF call failed: %s", e)

    # --- Fallback امن (بدون خروج از کار) ---
    ctx = _join_context(context)
    fallback = [
        "⚠️ حالت آفلاین/آزمایشی مولد فعال شد (HF در دسترس نیست).",
        "پرسش شما:",
        prompt,
    ]
    if ctx:
        fallback += ["", "خلاصهٔ زمینهٔ ارسالی:", ctx]

    fallback += [
        "",
        "پاسخ نمونه (template):",
        "در حال حاضر به سرویس تولید پاسخ متصل نیستیم. برای پاسخ نهایی یکی از کارهای زیر را انجام دهید:",
        "1) متغیرهای محیطی HF_TOKEN و MODEL_ENDPOINT را ست کنید و سرویس را دوباره اجرا کنید.",
        "2) از مسیر ingest/build_faiss.py ایندکس و زمینه را بسازید و سپس دوباره تست کنید.",
    ]
    return "\n".join(fallback)


# --- ابزارک‌های کمکی برای سلامت سرویس ---
def healthcheck() -> Dict[str, Any]:
    return {
        "provider": MODEL_PROVIDER,
        "has_token": bool(HF_TOKEN),
        "endpoint_set": bool(MODEL_ENDPOINT),
        "timeout_secs": REQUEST_TIMEOUT,
    }


# اجرای سریع محلی برای تست دستی
if __name__ == "__main__":
    demo = generate_answer(
        "سلام! یک پاسخ کوتاه بده.",
        context=["این یک متن زمینهٔ آزمایشی است تا ببینیم اتصال برقرار است یا نه."]
    )
    print(demo)
    print("health:", healthcheck())
