# app/ui.py
# رابط کاربری Streamlit برای منتور شخصی با حافظه مکالمه و لحن قابل انتخاب

import os
import textwrap
from pathlib import Path
import sys

import streamlit as st
from dotenv import load_dotenv

# اضافه کردن مسیر برای ایمپورت ماژول‌ها
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR / "app"))

# ایمپورت اجزای داخلی
from retriever import Retriever
from persona import SYSTEM_PERSONA, STYLE_PRESETS
from memory import ChatMemory

# پیکربندی صفحه
load_dotenv()
st.set_page_config(page_title="منتور شخصی", page_icon="🤖", layout="wide")
st.title("🤖 منتور شخصی با حافظه و سبک پاسخ سفارشی")

# تنظیمات API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

# تنظیمات سایدبار
with st.sidebar:
    st.subheader("تنظیمات پاسخ")
    if OPENAI_API_KEY:
        st.success("حالت آنلاین (با مدل زبانی)")
    else:
        st.warning("حالت آفلاین (بدون کلید OpenAI)")

    top_k = st.slider("تعداد نتایج بازیابی‌شده", 3, 15, 5)
    style_name = st.selectbox("سبک پاسخ", list(STYLE_PRESETS.keys()), index=0)
    st.caption("ایندکس باید در پوشه faiss_index موجود باشد (index.faiss و meta.json).")

# بارگذاری ایندکس
try:
    retriever = Retriever()
except Exception as e:
    st.error(
        f"❌ خطا در بارگذاری ایندکس: {e}\n"
        "ابتدا دستور زیر را اجرا کن:\n`python ingest/build_faiss.py`"
    )
    st.stop()

# حافظه مکالمه در Session State
if "memory" not in st.session_state:
    st.session_state["memory"] = ChatMemory()
memory: ChatMemory = st.session_state["memory"]

# ورودی کاربر
query = st.text_input("سؤالت یا موضوع موردنظر را بنویس:", placeholder="مثلاً: هدف مذاکره برد-برد چیست؟")
ask = st.button("پرسیدن")

# تابع تولید پاسخ با مدل زبانی
def llm_answer(context: str, q: str, style_desc: str) -> str:
    if not OPENAI_API_KEY:
        return None  # حالت آفلاین
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        history_text = memory.as_text()

        prompt = f"""
{SYSTEM_PERSONA}

سبک پاسخ: {style_desc}

گفتگوهای اخیر:
{history_text if history_text else "—"}

پرسش جدید: {q}

متون مرتبط (Context):
{context}

دستورالعمل:
- اگر پاسخ در متون نبود، بگو مطمئن نیستم و پیشنهاد مسیر جست‌وجو بده.
- در پایان، یک گام عملی سریع (Action) پیشنهاد کن.
"""

        r = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return r.choices[0].message.content

    except Exception as e:
        st.info(f"⚠️ مشکل در ارتباط با مدل زبانی: {e}")
        return None

# اجرا
if ask and query:
    memory.add("user", query)

    with st.spinner("در حال جست‌وجوی اسناد مرتبط..."):
        hits = retriever.search(query, k=top_k)

    if not hits:
        st.warning("هیچ سندی پیدا نشد. مطمئن شو پوشه data/ خالی نباشد و ایندکس ساخته شده باشد.")
    else:
        col_ans, col_refs = st.columns([2, 1])

        with col_refs:
            st.subheader("📚 اسناد مرتبط")
            for i, h in enumerate(hits, 1):
                with st.expander(f"{i}. {h['source']} (score={h['score']:.3f})", expanded=(i == 1)):
                    st.write(h["text"])

        with col_ans:
            st.subheader("💬 پاسخ منتور")
            context = "\n\n".join([f"[منبع: {h['source']}]\n{h['text']}" for h in hits])
            style_desc = STYLE_PRESETS.get(style_name, "")
            answer = llm_answer(context, query, style_desc)

            if not answer:
                # حالت آفلاین: خلاصه‌سازی ساده از نتایج
                bullets = []
                for h in hits:
                    snippet = h["text"].replace("\n", " ")
                    snippet = textwrap.shorten(snippet, width=220, placeholder="…")
                    bullets.append(f"• {snippet}")
                answer = "\n".join(bullets)

            st.write(answer)
            memory.add("assistant", answer)

st.caption("ساخته‌شده با ❤️ برای پروژه منتور شخصی | حافظه فعال + سبک پاسخ قابل تنظیم")
