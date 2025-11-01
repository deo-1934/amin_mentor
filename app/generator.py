
#FEYZ
#DEO
from __future__ import annotations
import os
import json
import requests
from typing import List, Dict, Any

# -----------------------
# تنظیمات ENV
# -----------------------
MODEL_PROVIDER   = os.getenv("MODEL_PROVIDER", "openai").strip().lower()
MODEL_ENDPOINT   = os.getenv("MODEL_ENDPOINT", "").strip()
HF_TOKEN         = os.getenv("HF_TOKEN", "").strip()
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL     = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
REQUEST_TIMEOUT  = float(os.getenv("REQUEST_TIMEOUT", "45"))


# -----------------------
# تابع بررسی سلامت
# -----------------------
def healthcheck() -> Dict[str, Any]:
    return {
        "provider": MODEL_PROVIDER,
        "hf_endpoint": MODEL_ENDPOINT if MODEL_PROVIDER == "huggingface" else None,
        "openai_model": OPENAI_MODEL if MODEL_PROVIDER == "openai" else None,
    }


# -----------------------
# ساخت پرامپت به سبک «دوست عاقل»
# -----------------------
def _build_hybrid_prompt(user_question: str, context_chunks: List[str]) -> str:
    ctx = "\n\n".join(f"[منبع {i+1}]\n{t}" for i, t in enumerate(context_chunks))

    prompt = (
        "نقش تو یک دوست عاقل و قابل اعتماد است. نه قضاوت می‌کنی، نه دستور می‌دی. "
        "کنار کاربر می‌نشینی و صادقانه بهش کمک می‌کنی تصمیم درست بگیرد.\n"
        "تو در زمینه‌ی مذاکره، تمرکز، مدیریت زمان و رشد شخصی تجربه داری و بلد هستی عملی و ساده حرف بزنی.\n"
        "لحن تو صمیمی، انسانی و واقع‌بین است. نه خشک باش و نه بیش از حد انگیزشی. "
        "از کلمات رسمی یا شعارگونه استفاده نکن. مستقیم، آرام و واقعی حرف بزن.\n"
        "هیچ‌وقت نگو «به عنوان مدل هوش مصنوعی» یا «منبع موجود نیست». همیشه سعی کن کمک واقعی بدی.\n"
        "تکرار بی‌دلیل نداشته باش. نصیحت خالی نده؛ به جاش بگو دقیقاً الان چه کار کوچیکی می‌تونه انجام بده.\n"
        "اگر سوال مبهم بود، اول بگو برداشتت چیه و بعد ادامه بده.\n\n"
        "خروجی تو باید در چهار بخش کوتاه و واضح باشد:\n"
        "۱. چیزی که من از وضعیتت می‌فهمم (هم‌دلانه و بدون قضاوت)\n"
        "۲. کارهایی که می‌تونی همین امروز انجام بدی (واقعی و قابل شروع)\n"
        "۳. نکاتی که باید حواست باشه خرابش نکنی (مثل هشدار دوستانه)\n"
        "۴. حرف آخرِ من بهت (یه جمله کوتاه که حس همراهی بده، نه شعار بازاری)\n\n"
        "اگر کاربر درباره‌ی رابطه با آدم‌ها، تمرکز یا کنترل احساس پرسید، "
        "خیلی واقعی و کاربردی جواب بده، با مثال از زندگی روزمره، نه تئوری.\n\n"
        f"[یادداشت‌ها و اطلاعات زمینه‌ای]\n{ctx}\n\n"
        f"[سؤال کاربر]\n{user_question}\n\n"
        "[پاسخ دوست عاقل]\n"
    )

    return prompt


# -----------------------
# فراخوانی مدل HuggingFace (در صورت نیاز)
# -----------------------
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
    r = requests.post(MODEL_ENDPOINT, headers=headers, data=json.dumps(payload), timeout=REQUEST_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"HF API error: {r.status_code} {r.text[:300]}")
    data = r.json()
    if isinstance(data, list) and data and "generated_text" in data[0]:
        return data[0]["generated_text"]
    if isinstance(data, dict) and "generated_text" in data:
        return data["generated_text"]
    return json.dumps(data)[:2000]


# -----------------------
# فراخوانی مدل OpenAI ChatCompletion
# -----------------------
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
            {
                "role": "system",
                "content": "You are a calm, wise, and trusted friend who gives practical, realistic, and kind advice in Persian."
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_new_tokens,
        "temperature": 0.75,
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=REQUEST_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"OpenAI API error: {r.status_code} {r.text[:300]}")
    data = r.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        return json.dumps(data)[:2000]


# -----------------------
# اینترفیس اصلی برای تولید پاسخ
# -----------------------
def generate_answer(user_question: str, context: List[str], max_new_tokens: int = 256) -> str:
    prompt = _build_hybrid_prompt(user_question=user_question, context_chunks=context)
    if MODEL_PROVIDER == "openai":
        answer = _call_openai(prompt, max_new_tokens=max_new_tokens)
    elif MODEL_PROVIDER == "huggingface":
        answer = _call_hf(prompt, max_new_tokens=max_new_tokens)
    else:
        raise RuntimeError(f"Unsupported MODEL_PROVIDER: {MODEL_PROVIDER}")

    tail_split_marker = "[سؤال کاربر]"
    if tail_split_marker in answer:
        answer = answer.split(tail_split_marker)[-1].strip()

    return answer.strip()
#FEYZ
#DEO
