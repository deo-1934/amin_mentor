#FEYZ
#DEO
# -*- coding: utf-8 -*-

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
from typing import Optional, List

from app.generator import generate_answer  # از فایل خودت، بدون تغییر

app = FastAPI(
    title="Amin Mentor API",
    description="Backend for Amin Mentor front-end chat",
    version="0.2.0",
)

# اجازه بدیم index.html که لوکال باز شده (file://) بتونه به http://localhost:8000/chat وصل بشه.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # در حالت dev بازه. بعداً می‌تونی محدودش کنی.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str            # متن سوال کاربر در UI
    creative_level: int     # اسلایدر خلاقیت (۱ تا ۵)
    max_new_tokens: int     # حداکثر طول پاسخ که کاربر می‌خواد (مثلا 200, 512, ...)


@app.get("/health")
def health():
    """
    تست سریع برای اینکه بفهمیم سرور زنده‌ست.
    """
    return {"status": "ok", "msg": "server is alive ❤️"}


@app.post("/chat")
def chat(req: ChatRequest):
    """
    این روت توسط front (web_ui/index.html) صدا زده می‌شه.

    کارهایی که می‌کنیم:
    1. ورودی UI رو می‌گیریم (message, creative_level, max_new_tokens)
    2. این ورودی رو تبدیل می‌کنیم به شکل مورد انتظار generate_answer()
       در generator.py تو:
          - query
          - context (الان نداریم، می‌ذاریم None)
          - temperature_*  (از creative_level می‌سازیم)
          - max_tokens_*   (از max_new_tokens می‌سازیم)
    3. از generate_answer خروجی (string) می‌گیریم
    4. همیشه جواب 200 و JSON استاندارد برمی‌گردونیم، حتی اگه مدل خطا بده
    """

    t0 = time.time()

    # --- نگاشت خلاقیت UI → temperature مدل ---
    level = req.creative_level
    if level < 1:
        level = 1
    if level > 5:
        level = 5

    temp_simple_map = {
        1: 0.15,
        2: 0.20,
        3: 0.25,
        4: 0.30,
        5: 0.35,
    }
    temp_deep_map = {
        1: 0.20,
        2: 0.30,
        3: 0.40,
        4: 0.50,
        5: 0.60,
    }

    temperature_simple = temp_simple_map[level]
    temperature_deep   = temp_deep_map[level]

    # --- نگاشت طول پاسخ UI → سقف توکن‌های مدل ---
    # user_budget = مثلا 200 یا 512 که از UI اومده
    def clamp(v, lo, hi):
        return max(lo, min(hi, v))

    user_budget = req.max_new_tokens

    max_simple = clamp(user_budget // 2, 64, 256)   # سبک/کوتاه
    max_deep   = clamp(user_budget,       128, 768) # جدی‌تر/کامل‌تر

    # فعلا context اضافی نداریم (RAG / حافظه مکالمه)،
    # ولی generate_answer نیاز به پارامتر context دارد و می‌تونه None قبول کنه.
    context_blocks: Optional[List[str]] = None

    try:
        # تماس با منطق اصلی تو (بدون دست زدن به generator.py)
        raw_answer_str = generate_answer(
            query=req.message,
            context=context_blocks,
            temperature_simple=temperature_simple,
            temperature_deep=temperature_deep,
            max_tokens_simple=max_simple,
            max_tokens_deep=max_deep,
        )

        safe_text = (str(raw_answer_str or "").strip())

        if not safe_text:
            # اگر مدل چیزی برنگردوند یا فقط رشته خالی بود
            safe_text = (
                "پیامت رسید ولی جواب نهایی تولید نشد. "
                "یه بار دیگه بگو الان دقیقاً کجا قفل شدی؟ "
                "فروش؟ قیمت‌گذاری؟ یا اعتماد به نفس جلوی مشتری؟"
            )

        took_ms = int((time.time() - t0) * 1000)

        return {
            "answer": safe_text,
            "contexts": [],     # بعداً می‌تونیم RAG / منابع رو اینجا بذاریم
            "took_ms": took_ms,
        }

    except Exception:
        # اگر هر خطایی در تماس با مدل افتاد (API key نبود، timeout شد، ...)
        # ما نمی‌ذاریم 500 بره بیرون.
        took_ms = int((time.time() - t0) * 1000)

        fallback_text = (
            "فعلاً دسترسی مستقیم به مدل برقرار نشد، "
            "ولی پیام تو رو دارم 🌿\n"
            "بگو الان مشکل اصلی دقیقا کجاست؟ "
            "۱. مشتری قانع نمی‌شه ۲. قیمت رو له می‌کنن ۳. اعتماد به نفس جلوی مشتری؟"
        )

        return {
            "answer": fallback_text,
            "contexts": [],
            "took_ms": took_ms,
        }

#FEYZ
#DEO
