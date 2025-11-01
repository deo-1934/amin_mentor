#FEYZ
#DEO
# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from typing import List, Dict, Any
import streamlit as st

# -------------------------------------------------
# اطمینان از دسترسی به ماژول‌های داخل app
# -------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.generator import generate_answer
from app import retriever


# -------------------------------------------------
# تنظیمات صفحه
# -------------------------------------------------
st.set_page_config(
    page_title="Amin Mentor",
    page_icon="💬",
    layout="centered",
)

st.title("Amin Mentor")


# -------------------------------------------------
# حافظهٔ مکالمه (Session Memory)
# -------------------------------------------------
if "history" not in st.session_state:
    # بدون type hint برای حذف هشدار Pylance
    st.session_state.history = []


def _append(role: str, content: str):
    """افزودن پیام به تاریخچه مکالمه"""
    st.session_state.history.append({"role": role, "content": content})


# -------------------------------------------------
# نمایش مکالمات قبلی در صفحه
# -------------------------------------------------
for turn in st.session_state.history:
    with st.chat_message("user" if turn["role"] == "user" else "assistant"):
        st.markdown(turn["content"])


#DEO
# -------------------------------------------------
# فرم ارسال پیام جدید
# -------------------------------------------------
with st.form("chat_form", clear_on_submit=True):
    user_msg = st.text_area(
        "پیامت رو بنویس:",
        height=120,
        placeholder="سلام! هر سوالی درباره استراتژی، تمرکز یا مسیر کسب‌وکار داری از من بپرس...",
    )
    submitted = st.form_submit_button("بفرست")

if submitted and user_msg.strip():
    user_text = user_msg.strip()

    # ۱. پیام کاربر به تاریخچه اضافه شود
    _append("user", user_text)

    # ۲. ساخت حافظه مکالمه برای مدل
    convo_lines = []
    for turn in st.session_state.history[-8:]:
        role_label = "کاربر" if turn["role"] == "user" else "منتور"
        convo_lines.append(f"{role_label}: {turn['content']}")
    conversation_block = "\n".join(convo_lines).strip()

    # ۳. بازیابی دانش مرتبط
    knowledge_chunks = []
    try:
        retrieved = retriever.retrieve(user_text, top_k=4)
        for r in retrieved[:4]:
            txt = r.get("text", "").strip()
            src = r.get("source", "")
            if txt:
                knowledge_chunks.append(f"{txt} (منبع:{src})")
    except Exception:
        knowledge_chunks = []

    knowledge_block = ""
    if knowledge_chunks:
        knowledge_block = "دانش داخلی مرتبط:\n" + "\n\n---\n\n".join(knowledge_chunks)

    # ۴. ساخت context نهایی برای مدل
    final_context_list = []
    if knowledge_block:
        final_context_list.append(knowledge_block)
    if conversation_block:
        final_context_list.append("گفتگو تا این لحظه:\n" + conversation_block)

    # ۵. دریافت پاسخ از مدل
    with st.spinner("در حال فکر کردن..."):
        try:
            answer_text = generate_answer(
                query=user_text,
                context=final_context_list,
            )
        except Exception:
            answer_text = (
                "الان اتصال من به مدل قطع شده. یک بار دیگه بپرس یا واضح‌تر بگو دنبال چی هستی."
            )

    # ۶. نمایش و ذخیره پاسخ
    _append("assistant", answer_text)
    with st.chat_message("assistant"):
        st.markdown(answer_text)
