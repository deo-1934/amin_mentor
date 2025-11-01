#FEYZ
#DEO
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

# تنظیم مسیر برای اطمینان از شناسایی پکیج app
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.generator import generate_answer
from app import retriever
import streamlit as st
from typing import List, Dict, Any

# تنظیمات صفحه
st.set_page_config(page_title="Amin Mentor", page_icon="💬", layout="centered")

# نگهداری تاریخچه گفتگو
if "history" not in st.session_state:
    st.session_state.history: List[Dict[str, Any]] = []

# عنوان
st.title("Amin Mentor")

# نمایش تاریخچه مکالمه
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

# تابع افزودن پیام به تاریخچه
def _append(role: str, content: str):
    st.session_state.history.append({"role": role, "content": content})

# اگر پیام جدید ارسال شد
if submitted and user_msg.strip():
    user_text = user_msg.strip()
    _append("user", user_text)

    # بازیابی زمینه (context) برای پاسخ دقیق‌تر
    ctx_items: List[str] = []
    try:
        retrieved = retriever.retrieve(user_text, top_k=4)
        ctx_items = [f"{r['text']}\n(منبع: {r.get('source','')})" for r in retrieved][:4]
    except Exception:
        ctx_items = []

    # تولید پاسخ نهایی از مدل
    with st.spinner("در حال فکر کردن..."):
        try:
            answer_text = generate_answer(user_text, context=ctx_items)
        except Exception:
            answer_text = (
                "در حال حاضر ارتباط با مدل برقرار نیست. لطفاً بعداً دوباره امتحان کن."
            )

    # افزودن پاسخ به تاریخچه و نمایش آن
    _append("assistant", answer_text)
    with st.chat_message("assistant"):
        st.markdown(answer_text)
