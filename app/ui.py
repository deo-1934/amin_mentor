#FEYZ
#DEO
# -*- coding: utf-8 -*-
import streamlit as st
from typing import List
from app.generator import generate_answer, healthcheck
from app import retriever

st.set_page_config(page_title="Amin Mentor", page_icon="💬", layout="centered")

# حداقل UI گفت‌وگومحور
if "history" not in st.session_state:
    st.session_state.history: List[dict] = []

st.title("Amin Mentor")

# فرم ورودی
with st.form("chat_form", clear_on_submit=True):
    user_msg = st.text_area("پیامت رو بنویس:", height=120, placeholder="سلام! از من هرچی می‌خوای بپرس…")
    submitted = st.form_submit_button("بفرست")

#DEO
def _append(role: str, content: str):
    st.session_state.history.append({"role": role, "content": content})

# نمایش تاریخچه
for turn in st.session_state.history:
    with st.chat_message("user" if turn["role"] == "user" else "assistant"):
        st.markdown(turn["content"])

# پردازش پیام
if submitted and user_msg.strip():
    _append("user", user_msg.strip())
    with st.spinner("در حال فکر کردن…"):
        # بازیابی اختیاریِ متن‌های مرتبط (بدون نمایش مستقیم به کاربر)
        ctx_items = []
        try:
            ctx = retriever.retrieve(user_msg.strip(), top_k=4)
            ctx_items = [f"{r['text']}\n(منبع: {r['source']})" for r in ctx][:4]
        except Exception:
            ctx_items = []

        text = generate_answer(
            user_msg.strip(),
            context=ctx_items,   # فقط برای کیفیت بهتر پاسخ؛ نمایش داده نمی‌شود
        )

    _append("assistant", text)

    # رندر آخرین پیام
    with st.chat_message("assistant"):
        st.markdown(text)

# وضعیت سلامت کوچک (فقط برای خودت—نه کاربر نهایی)
with st.expander("🛠 وضعیت سیستم (فقط برای توسعه)", expanded=False):
    hc = healthcheck()
    st.code(hc, language="python")
