#FEYZ
#DEO
import os
from typing import Literal, List, Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

# .env رو لود کن
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_CHEAP = os.getenv("OPENAI_MODEL_CHEAP", "gpt-4o-mini")
MODEL_DEEP = os.getenv("OPENAI_MODEL_DEEP", "gpt-4o-mini")

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI()

# اجازه دسترسی فرانت (حتی وقتی با file:// باز شده)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# حافظه مکالمه در حافظهٔ سرور (تا وقتی uvicorn روشنه)
if not hasattr(app.state, "memory"):
    app.state.memory = []  # list[{"role": "...", "content": "..."}]

class ChatRequest(BaseModel):
    message: str
    length: Literal["short", "normal", "long"] = "short"

class ChatResponse(BaseModel):
    answer: str

def build_length_instruction(length: str) -> str:
    if length == "short":
        return "پاسخ را خیلی کوتاه و مستقیم بده (۲ تا ۳ جمله خلاصه و اجرایی)."
    elif length == "long":
        return (
            "پاسخ را طولانی‌تر و مرحله‌به‌مرحله بده. دلیل هر قدم را هم توضیح بده. "
            "حداقل ۵-۶ جمله بنویس. مثال هم بزن."
        )
    else:
        return "پاسخ را شفاف و اجرایی بده در حد ۳ تا ۴ جمله. مستقیم باش."

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    user_question = req.message.strip()
    style_hint = build_length_instruction(req.length)

    if not user_question:
        return {"answer": "سوال خالی بود. یک سوال واقعی بپرس 🙂"}

    # اضافه کردن پیام کاربر به حافظه
    app.state.memory.append({
        "role": "user",
        "content": user_question
    })

    # ما فقط آخرین ~6 پیام را می‌فرستیم به مدل تا هزینه و طول کنترل شود
    recent_dialog: List[Dict[str, Any]] = app.state.memory[-6:]

    # پیام system + تاریخچه
    messages_for_model = [
        {
            "role": "system",
            "content": (
                "تو «منتور شخصی امین» هستی. خیلی کاربردی، واضح و بدون حاشیه جواب می‌دهی. "
                "تم تمرکز: بیزینس، فروش، مذاکره، تصمیم‌گیری. "
                "جواب باید قابل‌اجرا باشد. اگر سوال مبهم بود، اول سوال را واضح کن. "
                "از تئوری خالص بدون عمل قابل انجام پرهیز کن."
            ),
        },
        {
            "role": "system",
            "content": (
                f"طول پاسخ مورد انتظار کاربر: {req.length}. "
                f"{style_hint}"
            ),
        },
    ] + recent_dialog

    # تماس با مدل
    completion = client.chat.completions.create(
        model=MODEL_CHEAP,
        messages=messages_for_model,
        temperature=0.6,
        max_tokens=500,
    )

    raw_answer = ""
    if completion.choices and completion.choices[0].message:
        raw_answer = (completion.choices[0].message.content or "").strip()

    if raw_answer == "":
        raw_answer = (
            "الان نتونستم جواب مناسب تولید کنم. لطفاً دوباره بپرس یا مشخص‌تر بگو دقیقا کجا گیر کردی."
        )

    # پاسخ مدل هم به حافظه اضافه می‌شود
    app.state.memory.append({
        "role": "assistant",
        "content": raw_answer
    })

    return {"answer": raw_answer}
