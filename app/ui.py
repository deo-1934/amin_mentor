# app/ui.py
import sys
import os
import streamlit as st

# ------- مسیر پروژه برای ایمپورت ماژول‌های داخلی (Cloud-safe)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.retriever import retrieve
from app.generator import generate_answer

# ------- UI config
st.set_page_config(page_title="Amin Mentor", page_icon="🎓")
st.title("🎓 Amin Mentor")

st.markdown(
    "به منتور شخصی امین خوش اومدی! "
    "اینجا می‌تونی پرسش‌هات درباره‌ی کسب‌وکار، یادگیری، و توسعه فردی رو بپرسی 💬 "
    "و از هوش مصنوعی منتور، پاسخ تخصصی و شخصی‌سازی‌شده بگیری."
)

st.markdown("سؤال خودت رو بنویس 👇")

question = st.text_input(
    " ",
    placeholder="مثلاً: مهم‌ترین اصل توی یک مذاکره حرفه‌ای چیه؟",
)

if st.button("💬 پرسیدن از منتور"):
    if not question.strip():
        st.warning("اول یک سؤال بنویس 🙂")
    else:
        try:
            # 1. بازیابی اسناد مرتبط
            raw_docs = retrieve(question)

            # 2. استخراج فقط متن از نتایج (برای جلوگیری از خطای dict.strip)
            context_texts = []
            for item in raw_docs:
                if isinstance(item, dict) and "text" in item:
                    context_texts.append(item["text"])
                elif isinstance(item, str):
                    context_texts.append(item)

            # 3. تولید پاسخ با متن‌های تمیز
            answer = generate_answer(question, context_texts)

            st.markdown("### 🧠 پاسخ منتور")
            st.write(answer)

        except Exception as e:
            st.error(f"🚨 خطایی رخ داد: {e}")
else:
    st.caption("یک سؤال بنویس و روی دکمه بزن تا پاسخ منتور رو ببینی.")
