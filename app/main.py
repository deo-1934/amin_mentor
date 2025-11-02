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

from app.generator import generate_answer  # بدون تغییر در فایل تو

app = FastAPI(
    title="Amin Mentor API",
    description="Backend for Amin Mentor front-end chat",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    creative_level: int
    max_new_tokens: int
    force_new: Optional[bool] = False  # جدید: آیا کاربر می‌خواد جواب جدید تولید بشه؟


@app.get("/health")
def health():
    return {"status": "ok", "msg": "server is alive ❤️"}


@app.post("/chat")
def chat(req: ChatRequest):
    t0 = time.time()

    # map خلاقیت -> دما
    level = req.creative_level
    if level < 1:
        level = 1
    if level > 5:
        level = 5

    temp_simple_map = {1: 0.15, 2: 0.20, 3: 0.25, 4: 0.30, 5: 0.35}
    temp_deep_map   = {1: 0.20, 2: 0.30, 3: 0.40, 4: 0.50, 5: 0.60}

    temperature_simple = temp_simple_map[level]
    temperature_deep   = temp_deep_map[level]

    # map طول پاسخ -> max tokens
    def clamp(v, lo, hi):
        return max(lo, min(hi, v))

    user_budget = req.max_new_tokens
    max_simple = clamp(user_budget // 2, 64, 256)
    max_deep   = clamp(user_budget,       128, 768)

    # هنوز context نداریم
    context_blocks: Optional[List[str]] = None

    try:
        # اینجا تغییر اصلی:
        raw_answer_str = generate_answer(
            query=req.message,
            context=context_blocks,
            temperature_simple=temperature_simple,
            temperature_deep=temperature_deep,
            max_tokens_simple=max_simple,
            max_tokens_deep=max_deep,
            # این آرگومان جدید رو پایین تو generator اضافه می‌کنیم:
            force_new=req.force_new or False,
        )

        safe_text = (str(raw_answer_str or "").strip())
        if not safe_text:
            safe_text = (
                "پیامت رسید ولی جواب نهایی تولید نشد. "
                "یه بار دیگه بگو الان دقیقاً کجا قفل شدی؟ "
                "فروش؟ قیمت‌گذاری؟ یا اعتماد به نفس جلوی مشتری؟"
            )

        took_ms = int((time.time() - t0) * 1000)

        return {
            "answer": safe_text,
            "contexts": [],
            "took_ms": took_ms,
        }

    except Exception:
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
