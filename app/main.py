#FEYZ
#DEO

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time

# سعی می‌کنیم فقط چیزهایی رو از generator ایمپورت کنیم که مطمئنیم وجود دارن.
# فرض من: تو الان یه تابع داری به اسم generate_answer داخل app/generator.py
# اگر اسمش فرق می‌کنه (مثلا generate_response یا answer_question)، بعداً منو خبر کن که آپدیتش کنم.
from app.generator import generate_answer

app = FastAPI(
    title="Amin Mentor API",
    description="Backend for Amin Mentor front-end chat",
    version="0.1.0",
)

# باز کردن CORS برای تست لوکال (file:// -> http://localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # توی dev باز می‌ذاریم
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ورودی‌ای که فرانت می‌فرسته
class ChatRequest(BaseModel):
    message: str
    creative_level: int
    max_new_tokens: int

@app.get("/health")
def health():
    """
    این جایگزین healthcheck قبلیه.
    دیگه از generator چیزی به اسم healthcheck ایمپورت نمی‌کنیم.
    همین باعث می‌شه ImportError از بین بره و سرور بالا بیاد.
    """
    return {"status": "ok", "msg": "server is alive ❤️"}

@app.post("/chat")
def chat(req: ChatRequest):
    """
    این دقیقا همون آدرسیه که فرانت با fetch بهش POST می‌زنه.
    باید یه جواب با فیلدهای answer / contexts / took_ms بده.
    """

    t0 = time.time()

    # اینجا ما دو حالت داریم:
    # حالت ۱) generate_answer خودش همین ساختار رو برمی‌گردونه (answer/contexts/took_ms)
    # حالت ۲) generate_answer فقط یک متن خالی می‌ده یا فقط answer رو برمی‌گردونه.
    #
    # ما سعی می‌کنیم خروجی نهایی رو normalize کنیم تا فرانت نخوابه.

    raw = generate_answer(
        message=req.message,
        creative_level=req.creative_level,
        max_new_tokens=req.max_new_tokens,
    )

    # normalize:
    took_ms = int((time.time() - t0) * 1000)

    # اگر raw یک دیکشنری استاندارد بود:
    if isinstance(raw, dict):
        answer_text = raw.get("answer", "")
        contexts = raw.get("contexts", [])
        duration = raw.get("took_ms", took_ms)
    else:
        # اگر raw مثلا فقط یه استرینگ متن بوده
        answer_text = str(raw)
        contexts = []
        duration = took_ms

    # حالا پاسخی که دقیقا UI انتظار داره:
    return {
        "answer": answer_text if answer_text else "پاسخی از مدل دریافت نشد 🌱",
        "contexts": contexts,
        "took_ms": duration,
    }

#FEYZ
#DEO
