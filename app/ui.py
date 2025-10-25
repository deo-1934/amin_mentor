# app/ui.py
import os
from pathlib import Path
import textwrap

import streamlit as st
from dotenv import load_dotenv

from settings import UIConfig, DEFAULT_TOP_K, DEFAULT_EMBED_MODEL
from retriever import Retriever

# ---- Bootstrap ----
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

st.set_page_config(page_title="Amin Mentor", page_icon="🧠", layout="wide")
cfg = UIConfig()

# ---- Sidebar ----
st.sidebar.title("⚙️ تنظیمات")
mode = st.sidebar.radio("حالت پاسخ", ["آفلاین (بدون LLM)", "آنلاین (با LLM)"], index=0)
top_k = st.sidebar.slider("تعداد نتایج بازیابی (k)", 1, 15, DEFAULT_TOP_K, 1)
embed_model_name = st.sidebar.text_input("مدل امبدینگ", value=DEFAULT_EMBED_MODEL)
openai_key = st.sidebar.text_input("OpenAI API Key (برای حالت آنلاین)", type="password")

st.sidebar.caption("ایندکس باید در `faiss_index/` حاضر باشد (index.faiss + meta.json).")

# ---- Title ----
st.title(cfg.title)
st.write(cfg.description)

# ---- Load retriever ----
@st.cache_resource(show_spinner=True)
def _get_retriever(name: str) -> Retriever:
    return Retriever(embed_model=name)

try:
    retriever = _get_retriever(embed_model_name)
except Exception as e:
    st.error(f"❌ خطا در بارگذاری ایندکس/مدل: {e}")
    st.stop()

# ---- Query input ----
col_q1, col_q2 = st.columns([4, 1])
with col_q1:
    query = st.text_input("❓ پرسش شما", placeholder="مثلاً: بهترین شیوه مذاکره در شرایط فشار زمانی چیست؟")
with col_q2:
    ask = st.button("جست‌وجو", use_container_width=True)

# ---- Helper: Offline summarizer ----
def offline_answer(query: str, hits):
    # پاسخ خیلی ساده بر اساس قطعات بازیابی‌شده (بدون LLM)
    if not hits:
        return "موردی پیدا نشد."
    joined = "\n\n".join([f"- {h['text']}" for h in hits])
    answer = textwrap.shorten(joined, width=900, placeholder=" ...")
    return f"**خلاصه‌ی سریع از متون مرتبط:**\n\n{answer}"

# ---- Main action ----
if ask and query:
    with st.spinner("در حال جست‌وجوی اسناد مرتبط..."):
        hits = retriever.search(query, k=top_k)

    if not hits:
        st.warning("هیچ سندی پیدا نشد. پوشه `data/` را بررسی کن و اگر خالی است، فایل متنی اضافه کن و دوباره ایندکس بساز.")
    else:
        col_ans, col_refs = st.columns([2, 1], gap="large")

        # Answer panel
        with col_ans:
            st.subheader("🧩 پاسخ")
            if mode.startswith("آفلاین"):
                st.markdown(offline_answer(query, hits))
            else:
                if not openai_key:
                    st.info("برای حالت آنلاین، کلید OpenAI را در سایدبار وارد کن. فعلاً حالت آفلاین نمایش داده می‌شود.")
                    st.markdown(offline_answer(query, hits))
                else:
                    # اینجا می‌تونی فراخوان LLM خودت را بنویسی (فعلاً ساده نگه می‌داریم)
                    st.markdown(offline_answer(query, hits))
                    st.caption("💡 اتصال LLM قابل افزودن است (تولید پاسخ نهایی بر اساس نتایج بازیابی‌شده).")

        # References panel
        with col_refs:
            st.subheader("📎 منابع")
            for i, h in enumerate(hits, 1):
                with st.expander(f"{i}. {h.get('source','نامشخص')}  •  امتیاز: {h['score']:.3f}  •  chunk: {h.get('chunk_idx','-')}"):
                    st.write(h.get("text", "—"))
                    meta_line = []
                    if h.get("path"): meta_line.append(f"`{h['path']}`")
                    if h.get("source"): meta_line.append(f"source: **{h['source']}**")
                    if meta_line:
                        st.caption(" | ".join(meta_line))
