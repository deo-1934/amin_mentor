#FEYZ
#DEO
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

# -------------------------------------------------
# اطمینان از اینکه پایتون می‌تونه پکیج app رو پیدا کنه
# -------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# حالا می‌تونیم ماژول‌های داخل پروژه رو ایمپورت کنیم
from app.generator import generate_answer, healthcheck  # تولید پاسخ
from app import retriever  # ماژول جست‌وجوی متن/دانش

import streamlit as st
from typing import List, Dict, Any

# -------------------------------------------------
# تنظیمات صفحه
# -------------------------------------------------
st.set_page_config(
    page_title="Amin Mentor",
    page_icon="💬",
    layout="centered",
)

# نگهداری تاریخچه چت در session_state
if "history" not in st.session_state:
    # هر آیتم: {"role": "user" | "assistant", "content": str}
    st.session_state.history: List[Dict[str, Any]] = []

# عنوان بالای صفحه
st.title("Amin Mentor")


# یک تابع کوچک برای اضافه کردن پیام به هیستوری
def _append(role: str, content: str):
    st.session_state.history.append(
        {
            "role": role,
            "content": content,
        }
    )


# رندر تاریخچه مکالمه تا اینجا
for turn in st.session_state.history:
    with st.chat_message("user" if turn["role"] == "user" else "assistant"):
        st.markdown(turn["content"])

#DEO
# فرم ورودی پیام کاربر
with st.form("chat_form", clear_on_submit=True):
    user_msg = st.text_area(
        "پیامت رو بنویس:",
        height=120,
        placeholder="سلام! از من هر چیزی در مورد کسب‌وکار، استراتژی، اولویت‌بندی کار یا مسیر حرکت بپرس...",
    )
    submitted = st.form_submit_button("بفرست")

# اگر پیام جدید ارسال شد
if submitted and user_msg and user_msg.strip():
    user_text = user_msg.strip()

    # 1. پیام کاربر را به تاریخچه اضافه کن
    _append("user", user_text)

    # 2. درجا سعی کن از دانش داخلی/متن‌های ما بازیابی مرتبط بیاری
    ctx_items: List[str] = []
    try:
        retrieved = retriever.retrieve(user_text, top_k=4)
        # هر تکه رو به صورت "متن (منبع)" نگه می‌داریم
        ctx_items = [
            f"{r['text']}\n(منبع: {r.get('source','')})"
            for r in retrieved
        ][:4]
    except Exception:
        # اگه retriever خراب بود، گفتگو نباید بترکه
        ctx_items = []

    # 3. تولید پاسخ نهایی یک‌تکه
    with st.spinner("در حال فکر کردن…"):
        try:
            answer_text = generate_answer(
                user_text,
                context=ctx_items,   # برای کیفیت بهتر پاسخ
            )
        except Exception as e:
            # اگر generator ارور بده، حداقل یه پیام منطقی بده
            answer_text = (
                "در حال حاضر بخش تولید پاسخ فعال نیست یا به مدل متصل نشده. "
                "زیرساخت در حال آماده‌سازی است، ولی پیام تو ثبت شد."
            )

    # 4. پاسخ رو توی تاریخچه بچسبون
    _append("assistant", answer_text)

    # 5. فقط آخرین پیام دستیار رو (که همین الان ساختیم) رندر کن
    with st.chat_message("assistant"):
        st.markdown(answer_text)


# بلوک وضعیت سیستم (فقط برای خودت به عنوان dev، کاربر نهایی لازم نیست بازش کنه)
with st.expander("🛠 وضعیت سیستم (فقط برای توسعه)", expanded=False):
    try:
        hc = healthcheck()
    except Exception as e:
        hc = {
            "error": "healthcheck failed",
            "detail": str(e),
        }
    st.code(hc, language="python")
