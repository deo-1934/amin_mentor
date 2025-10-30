# app/generator.py
from __future__ import annotations
import os
import requests
from typing import List, Dict, Any

# --- تنظیمات مدل برای Cloud (از secrets یا env) ---
MODEL_PROVIDER   = os.getenv("MODEL_PROVIDER", "huggingface")
MODEL_ENDPOINT   = os.getenv("MODEL_ENDPOINT", "https://api-inference.huggingface.co/models/gpt2")
HF_TOKEN         = os.getenv("HF_TOKEN", "")
REQUEST_TIMEOUT  = float(os.getenv("REQUEST_TIMEOUT", "30"))

HEADERS = {}
if MODEL_PROVIDER == "huggingface" and HF_TOKEN:
    HEADERS["Authorization"] = f"Bearer {HF_TOKEN}"


def healthcheck() -> Dict[str, Any]:
    return {
        "provider": MODEL_PROVIDER,
        "has_token": bool(HF_TOKEN),
        "endpoint_set": bool(MODEL_ENDPOINT),
        "timeout_secs": REQUEST_TIMEOUT,
    }


def _call_text_generation_api(prompt: str, max_new_tokens: int = 200) -> str:
    """
    این تابع الان برای HuggingFace endpoint طراحی شده.
    اگه بعدا رفتیم روی مدل دیگه (میزبان خصوصی، لوکال و غیره)،
    فقط همین تابع رو عوض می‌کنیم.
    """
    if MODEL_PROVIDER == "huggingface":
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_new_tokens,
                "temperature": 0.7,
                "top_p": 0.9,
                "do_sample": True,
            }
        }
        try:
            resp = requests.post(
                MODEL_ENDPOINT,
                headers=HEADERS,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            # HF بعضی وقتا لیست dict میده با "generated_text"
            if isinstance(data, list) and len(data) and "generated_text" in data[0]:
                return data[0]["generated_text"]
            # fallback
            return str(data)
        except Exception as e:
            return f"(خطای مدل زبانی: {e})"

    # fallback در صورتی که provider ناشناخته باشه
    return "(مدل زبانی در دسترس نیست.)"


def _build_hybrid_prompt(user_question: str,
                         context_chunks: List[str]) -> str:
    """
    اینجا prompt اصلی ما ساخته میشه.
    این prompt:
    - هویت منتور امین رو تعریف می‌کنه
    - داده‌ی RAG رو تزریق می‌کنه
    - سوال کاربر رو می‌ذاره
    """

    merged_context = "\n\n".join(
        f"- {chunk.strip()}" for chunk in context_chunks if chunk and chunk.strip()
    )

    # سبک و هویت برند اینجاست 🔥
    system_instructions = (
        "تو یک منتور شخصی فارسی‌زبان هستی به نام «منتور امین». "
        "تو باید راهنمایی عمل‌گرا، محترمانه و قابل اجرا بدی. "
        "توضیحاتت باید کوتاه، صریح و مهربان باشه. "
        "در صورت امکان از مثال‌های واقعی و قدم‌های عملی استفاده کن. "
        "اگر موضوع مربوط به رشد فردی، اعتماد به نفس، مذاکره، یادگیری یا توسعه فردی است "
        "اولویت با آموزه‌های داخلی امین است. "
        "اگر داده‌ی داخلی کافی نبود، از دانش عمومی خودت کمک بگیر "
        "ولی لحن و هویت «منتور امین» را حفظ کن."
    )

    prompt = f"""
[هویت منتور]
{system_instructions}

[دانش داخلی (context)]
{merged_context if merged_context else "(در حال حاضر داده داخلی زیادی موجود نیست.)"}

[سوال کاربر]
{user_question}

[دستور تولید پاسخ]
پاسخی روان و حمایتی بده. در حد چند پاراگراف، مشخص و کاربردی.
از کلی‌گوییِ بی‌فایده و نصیحت تکراری دوری کن.
اگر لازم است مرحله‌های عملی بده (قدم ۱، قدم ۲ و ...).
    """.strip()

    return prompt


def generate_hybrid_answer(
    user_question: str,
    retrieved_docs: List[Dict[str, Any]],
    max_new_tokens: int = 200,
) -> str:
    """
    این همون قلب حالت Hybrid هست.
    ورودی:
      - سوال کاربر
      - سندهای retrieve شده از دیتاهای اختصاصی (لیست دیکشنری با keys مثل text, source,...)

    خروجی:
      - پاسخ مکالمه‌ای ولی آگاه از دیتای ما
    """

    # فقط محتوا رو بکشیم بیرون
    context_strings = []
    for hit in retrieved_docs:
        # هر hit شکلی شبیه {"text": "...", "source": "...", ...} داره
        if "text" in hit and isinstance(hit["text"], str):
            context_strings.append(hit["text"])

    prompt = _build_hybrid_prompt(
        user_question=user_question,
        context_chunks=context_strings
    )

    answer = _call_text_generation_api(prompt, max_new_tokens=max_new_tokens)

    # یه تمیزکاری خیلی ساده:
    # گاهی HF بخشی از prompt رو echo می‌کنه، ما فقط انتهای تولید رو می‌خوایم.
    # استراتژی ساده: آخرین حضور سوال کاربر رو پیدا کن و بعدش رو نگه دار.
    tail_split_marker = "[سوال کاربر]"
    if tail_split_marker in answer:
        answer = answer.split(tail_split_marker)[-1].strip()
    return answer.strip()
