#FEYZ
#DEO
import os
from typing import Literal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# فقط وقتی نیاز داریم کلاینت بسازیم می‌سازیم
from openai import OpenAI

# env ها رو لود کن (لوکال). روی Render خودش از Environment استفاده می‌کنه
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_CHEAP = os.getenv("OPENAI_MODEL_CHEAP", "gpt-4o-mini")
MODEL_DEEP = os.getenv("OPENAI_MODEL_DEEP", "gpt-4o-mini")

app = FastAPI(title="Amin Mentor API", version="1.0.0")

# اجازه بدیم از هر فرانت (HTML, Streamlit, ...) بشه به این API وصل شد
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# روت اصلی برای تست سلامت سرویس
@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Amin Mentor API is running successfully 🚀",
    }

# بدنهٔ ریکوئست برای چت
class ChatRequest(BaseModel):
    message: str
    mode: Literal["cheap", "deep"] = "cheap"

@app.post("/chat")
async def chat(request: ChatRequest):
    # اگر کلید OpenAI ست نشده باشه، خطای شفاف برگردون
    if not OPENAI_API_KEY:
        return {
            "error": "OPENAI_API_KEY is missing on server",
            "detail": "Set OPENAI_API_KEY in Render -> Environment",
        }

    # انتخاب مدل ارزون یا عمیق
    model_name = MODEL_DEEP if request.mode == "deep" else MODEL_CHEAP

    # ساخت کلاینت در لحظه (نه در import اولیه) تا سرور بدون کلید نخوابه
    client = OpenAI(api_key=OPENAI_API_KEY)

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": request.message}
            ],
        )
        return {"response": response.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}

#DEO
