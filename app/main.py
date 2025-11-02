#FEYZ
#DEO

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.generator import generate_answer

# مدل ورودی برای /chat
class ChatRequest(BaseModel):
    message: str
    creative_level: int
    max_new_tokens: int

app = FastAPI(
    title="Amin Mentor API",
    description="Backend for Amin Mentor front-end chat",
    version="0.1.0",
)

# CORS برای اینکه index.html محلی بتونه بهش POST بزنه
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # در فاز dev بازه
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    """
    endpoint ساده برای تست سلامت.
    فرانت مستقیم ازش استفاده نمی‌کنه ولی برای تست دستی خوبه.
    """
    return {"status": "ok", "msg": "server is alive ❤️"}

@app.post("/chat")
def chat(req: ChatRequest):
    """
    این همون مسیریه که فرانت با fetch() صداش می‌زنه.
    خروجی باید دقیقا شامل answer / contexts / took_ms باشه.
    """
    result = generate_answer(
        message=req.message,
        creative_level=req.creative_level,
        max_new_tokens=req.max_new_tokens,
    )
    return result

#FEYZ
#DEO
