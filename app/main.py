#FEYZ
#DEO
import os
from typing import Literal, List, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

# بارگذاری متغیرهای محیطی از .env
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_CHEAP = os.getenv("OPENAI_MODEL_CHEAP", "gpt-4o-mini")
MODEL_DEEP = os.getenv("OPENAI_MODEL_DEEP", "gpt-4o-mini")

client = OpenAI(api_key=OPENAI_API_KEY)

# ایجاد اپ اصلی FastAPI
app = FastAPI(title="Amin Mentor API", version="1.0.0")

# فعال‌سازی CORS برای دسترسی از فرانت‌اند (Streamlit یا HTML)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# مسیر اصلی برای تست سرویس
@app.get("/")
def root():
    return {"status": "ok", "message": "Amin Mentor API is running successfully 🚀"}

# مدل داده برای چت
class ChatRequest(BaseModel):
    message: str
    mode: Literal["cheap", "deep"] = "cheap"

# مسیر چت اصلی
@app.post("/chat")
async def chat(request: ChatRequest):
    model_name = MODEL_DEEP if request.mode == "deep" else MODEL_CHEAP

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": request.message}],
        )
        return {"response": response.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}

#DEO
