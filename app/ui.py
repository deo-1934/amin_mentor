#FEYZ
#DEO
# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from typing import List, Dict, Any
import streamlit as st

# اضافه کردن ریشه پروژه به sys.path تا ایمپورت‌های app.* روی Streamlit Cloud هم کار کنن
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.generator import generate_answer
from app import retriever

# پیکربندی صفحه
st.set_page_config(
    page_title="Amin Mentor",
    page_icon="💬",
    layout="centered",
)

# نگه داشتن تاریخچه مکالمه در session_state
if "history" not in st.session_state:
    st.session_state.history: List[Dict[str, Any]] = []

# نمایش تاریخچه مکالمه موجود
for turn in st.session_state.history:
    with st.chat_message("user" if turn["role"] == "user" else "assistant"):
        st.markdown(turn["content"])

def _append(role: str, content: str):
    st.session_state.history.append({"role": role, "content": content})

#DEO
# فرم ورودی برای پیام جدید
with st.form("chat_form", clear_on_submit=True):
    user_msg = st.text_area(
        "پیامت رو بنویس:",
        height=120,
        placeholder="سلام! از من هر چیزی در مورد کسب‌وکار، استراتژی، اولویت‌بندی کار یا مسیر حرکت بپرس...",
    )
    submitted = st.form_submit_button("بفرست")

if submitted and user_msg.strip():
    user_text = user_msg.strip()

    # پیام کاربر رو الان تو هیستوری بذار که بلافاصله در UI هم دیده بشه
    _append("user", user_text)

    # ۱. حافظه مکالمه (آخرین 6 پیام) فقط برای مدل
    memory_lines: List[str] = []
    for turn in st.session_state.history[-6:]:
        role_label = "کاربر" if turn["role"] == "user" else "منتور"
        memory_lines.append(f"{role_label}: {turn['content']}")
    memory_block = "\n".join(memory_lines).strip()

    # ۲. بازیابی دانش (retriever)
    # این بخش متن محتوای آموزشی/کتاب/دیتای داخلیه، نه تکرار گفت‌وگو
    knowledge_snippets: List[str] = []
    try:
        retrieved = retriever.retrieve(user_text, top_k=4)
        for r in retrieved[:4]:
            snippet_text = r.get("text", "").strip()
            src = r.get("source", "")
            if snippet_text:
                # این همون چیزی‌ه که می‌خوای تو پاسخ‌های آفلاین استفاده بشه
                knowledge_snippets.append(f"{snippet_text}\n(منبع: {src})")
    except Exception:
        knowledge_snippets = []

    # ۳. ساخت context نهایی برای generate_answer:
    # اول حافظه مکالمه میاد (برای اینکه مدل بفهمه "ادامه بده" یعنی چی)
    # بعد محتواهای دانشی میاد
    # اما: ما به generate_answer می‌گیم کل اینا context ـه.
    # generate_answer خودش مرحله‌بندی داره (smalltalk / rule / retrieval / model)
    # و در مرحله retrieval فقط از اولین آیتم context استفاده می‌کنه،
    # پس باید ترتیب رو طوری بچینیم که "دانش" بیاد جلو، نه حافظه.
    #
    # ترفند: اول knowledge_snippets و در آخر memory_block.
    # یعنی مرحله ۲ از دانش جواب می‌سازه، نه از لاگ مکالمه.
    full_context: List[str] = []
    full_context.extend(knowledge_snippets)
    if memory_block:
        full_context.append("گفتگو تا اینجا:\n" + memory_block)

    # ۴. تولید پاسخ
    with st.spinner("در حال فکر کردن..."):
        try:
            answer_text = generate_answer(
                query=user_text,
                context=full_context
            )
        except Exception:
            answer_text = (
                "الان مطمئن نیستم جواب قطعی بدم. یه ذره واضح‌تر بگو دقیقاً دنبال چی هستی تا بتونم کمک کنم."
            )

    # ۵. جواب رو هم در تاریخچه ذخیره کن و هم نشون بده
    _append("assistant", answer_text)

    with st.chat_message("assistant"):
        st.markdown(answer_text)
