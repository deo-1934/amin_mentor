#FEYZ
#DEO
# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from typing import List, Dict, Any
import streamlit as st

# -------------------------------------------------
# اطمینان از اینکه ایمپورت ماژول‌های داخل app توی Streamlit Cloud هم کار کنه
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
# State مکالمه
# هر پیام یک دیکشنری مثل {"role": "user"|"assistant", "content": "..."}
# -------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history: List[Dict[str, Any]] = []


def _append(role: str, content: str):
    """افزودن پیام به تاریخچه سشن"""
    st.session_state.history.append({"role": role, "content": content})


# -------------------------------------------------
# نمایش تاریخچه چت روی صفحه (حبابی)
# -------------------------------------------------
for turn in st.session_state.history:
    with st.chat_message("user" if turn["role"] == "user" else "assistant"):
        st.markdown(turn["content"])


#DEO
# -------------------------------------------------
# فرم ورودی پیام جدید
# -------------------------------------------------
with st.form("chat_form", clear_on_submit=True):
    user_msg = st.text_area(
        "پیامت رو بنویس:",
        height=120,
        placeholder="سلام! هر سوالی درباره مسیر کسب‌وکار، تمرکز، اولویت‌بندی کار یا استراتژی داری از من بپرس...",
    )
    submitted = st.form_submit_button("بفرست")


if submitted and user_msg.strip():
    user_text = user_msg.strip()

    # ۱. پیام کاربر الان به تاریخچه اضافه بشه که فوری توی UI هم دیده بشه
    _append("user", user_text)

    # -------------------------------------------------
    # ۲. ساخت memory واقعی برای مدل
    # -------------------------------------------------
    # اینجا ما لاگ مکالمه رو تقریباً مثل یک چت واقعی برای مدل در میاریم
    # یعنی مدل بدونه "چی پرسیده شد" و "چی جواب داده شد"
    # و این باعث می‌شه وقتی کاربر میگه "ادامه بده" مدل بدونه ادامهٔ چی.
    #
    # محدودش می‌کنیم به آخرین ~8 نوبت برای اینکه توکن نسوزونیم
    # فرمت گفت‌وگو رو واضح می‌سازیم:
    # کاربر: ...
    # منتور: ...
    convo_lines: List[str] = []
    for turn in st.session_state.history[-8:]:
        if turn["role"] == "user":
            convo_lines.append(f"کاربر: {turn['content']}")
        else:
            convo_lines.append(f"منتور: {turn['content']}")
    conversation_block = "\n".join(convo_lines).strip()

    # -------------------------------------------------
    # ۳. بازیابی دانش مرتبط (retriever)
    # -------------------------------------------------
    # این فقط دانش دانشی‌ه (از متن‌ها و یادداشت‌ها و کتاب و ...)،
    # نه لاگ مکالمه. اینو هم به مدل می‌دیم تا جوابش دقیق‌تر بشه.
    knowledge_chunks: List[str] = []
    try:
        retrieved = retriever.retrieve(user_text, top_k=4)
        for r in retrieved[:4]:
            txt = r.get("text", "").strip()
            src = r.get("source", "")
            if txt:
                # منبع رو نرم و کم‌حاشیه نگه می‌داریم که مدل فقط الهام بگیره
                knowledge_chunks.append(f"{txt} (منبع:{src})")
    except Exception:
        knowledge_chunks = []

    # این بلاک دانشی رو به یک رشته تبدیل می‌کنیم که بعد به مدل تزریق بشه
    # (اگر چیزی برگشته باشه)
    if knowledge_chunks:
        knowledge_block = "دانش داخلی مرتبط:\n" + "\n\n---\n\n".join(knowledge_chunks)
    else:
        knowledge_block = ""

    # -------------------------------------------------
    # ۴. ساخت context نهایی برای generate_answer
    # -------------------------------------------------
    # حالا به جای بازی با خلاصه نصفه و نیمه،
    # ما دو چیز رو بهم می‌چسبونیم:
    # - history مکالمه (conversation_block)
    # - دانش دامنه‌ای (knowledge_block)
    #
    # این context در نهایت میره توی prompt مدل داخل generator.py
    # و generator.py بسته به سختی سوال تصمیم می‌گیره مدل ارزون‌تر یا قوی‌تر رو صدا بزنه.
    final_context_list: List[str] = []

    if knowledge_block:
        final_context_list.append(knowledge_block)

    if conversation_block:
        final_context_list.append(
            "گفتگو تا این لحظه:\n" + conversation_block
        )

    # -------------------------------------------------
    # ۵. گرفتن پاسخ از مدل
    # -------------------------------------------------
    with st.spinner("در حال فکر کردن..."):
        try:
            answer_text = generate_answer(
                query=user_text,
                context=final_context_list,
            )
        except Exception:
            # اگر مدل نپرسد/شبکه قطع شود و ...:
            answer_text = (
                "الان اتصال من به مدل فکری قطع شد. یک بار دیگه بپرس یا دقیق‌تر بگو الان دقیقا دنبال چه راهنمایی هستی."
            )

    # -------------------------------------------------
    # ۶. نمایش و آپدیت تاریخچه
    # -------------------------------------------------
    _append("assistant", answer_text)

    with st.chat_message("assistant"):
        st.markdown(answer_text)
