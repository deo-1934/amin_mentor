# app/generator.py
from typing import List, Dict, Any
import textwrap

def _build_answer(question: str, context_chunks: List[str]) -> str:
    """
    یک پاسخ شبه-منتور می‌سازیم بر اساس سوال و تکه‌های متن پیدا شده.
    اینجا عمداً مدل زبانی واقعی صدا زده نمی‌شود (برای دمو پایدار در Cloud).
    """

    # context_chunks: لیستی از متن‌های مرتبطی که retriever برگردونده
    merged_context = "\n".join(context_chunks[:3]) if context_chunks else ""

    # یه فرمت دوستانه، شبیه منتور
    answer = f"""
    سوال تو: {question}

    چیزی که از منابع متنی مرتبط فهمیدم:
    {merged_context}

    نکته منتور:
    - اول روی درک موقعیت و نیاز طرف مقابل تمرکز کن.
    - بعد سعی کن کاری که می‌خوای انجام بشه رو واضح و بدون حاشیه بگی.
    - و همیشه یک قدم عملی مشخص برای بعد تعریف کن (هم برای خودت، هم برای طرف مقابل).

    اگر می‌خوای بیشتر بازش کنم، می‌تونی سوالت رو دقیق‌تر و با مثال بپرسی (مثلاً: «من با مدیرم مذاکره دارم سر افزایش حقوق، چی بگم؟»).
    """.strip()

    # قشنگ‌ترش می‌کنیم یکم
    return textwrap.dedent(answer)

def generate_answer(question: str, context_chunks: List[str]) -> str:
    """
    API اصلی که ui.py صدا می‌زند.
    """
    # اگر ورودی خالیه
    if not question or not isinstance(question, str):
        return "سؤالت نامعتبره. لطفاً یه سؤال معنی‌دار بپرس 🙂"

    # اگه به هر دلیل context_chunks None یا چیز عجیبه
    if not isinstance(context_chunks, list):
        context_chunks = []

    return _build_answer(question, context_chunks)

def healthcheck() -> Dict[str, Any]:
    """
    اطلاعات برای دیباگ (الان خیلی ساده نگه می‌داریم)
    """
    return {
        "provider": "local-demo",
        "huggingface_used": False,
        "ok": True,
    }
