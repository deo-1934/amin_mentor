#FEYZ
#DEO
# -*- coding: utf-8 -*-
import os
import json
import time
from typing import Dict, Any, List

import streamlit as st

# تلاش برای ایمپورت به هر دو حالت اجرا (داخل پکیج/مستقل)
try:
    from app.generator import generate_answer, load_settings
except Exception:
    from generator import generate_answer, load_settings

# ------------------------- Page Config -------------------------
st.set_page_config(
    page_title="Amin Mentor — Chat",
    page_icon="🤝",
    layout="wide"
)

# ------------------------- Sidebar (تنظیمات) -------------------------
settings = load_settings()

with st.sidebar:
    st.markdown("### ⚙️ تنظیمات")
    provider_options = ["openai", "huggingface", "offline"]
    try:
        default_idx = provider_options.index(settings.get("MODEL_PROVIDER", "openai"))
    except ValueError:
        default_idx = 0
    model_provider = st.selectbox("Model Provider", provider_options, index=default_idx)

    # OpenAI
    openai_model = st.text_input(
        "OPENAI_MODEL",
        value=settings.get("OPENAI_MODEL", "gpt-4o-mini"),
        placeholder="gpt-4o-mini / gpt-4.1-mini / …",
        help="وقتی Provider = openai است"
    )
    openai_api_key = st.text_input(
        "OPENAI_API_KEY",
        value=settings.get("OPENAI_API_KEY", ""),
        type="password"
    )

    # HuggingFace
    model_endpoint = st.text_input(
        "HF MODEL_ENDPOINT",
        value=settings.get("MODEL_ENDPOINT", ""),
        placeholder="https://api-inference.huggingface.co/models/gpt2",
        help="وقتی Provider = huggingface است"
    )
    hf_token = st.text_input(
        "HF_TOKEN",
        value=settings.get("HF_TOKEN", ""),
        type="password"
    )

    temperature = st.slider("Temperature", 0.0, 1.5, value=0.2, step=0.05)
    max_new_tokens = st.slider("Max new tokens", 16, 1024, value=256, step=16)
    top_k = st.slider("Top-K Retrieval", 1, 10, value=5, step=1)

    st.divider()
    if st.button("🧹 پاک‌سازی تاریخچه", use_container_width=True):
        st.session_state.messages = []
        st.experimental_rerun()

#DEO
# ------------------------- Header -------------------------
st.markdown("## منتور شخصی امین")
st.caption("چتِ تمیز و سریع؛ پاسخ‌ها به شکل **مقدمه / هسته / جمع‌بندی** نمایش داده می‌شوند.")

# ------------------------- Session State -------------------------
if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, str]] = []

# رندر تاریخچهٔ پیام‌ها
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ------------------------- Chat Input -------------------------
prompt = st.chat_input("پیام خود را بنویسید…")
if prompt:
    # 1) نمایش پیام کاربر
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2) فراخوانی ژنراتور
    cfg: Dict[str, Any] = dict(
        model_provider=model_provider,
        # OpenAI
        openai_model=openai_model,
        openai_api_key=openai_api_key,
        # HF
        model_endpoint=model_endpoint,
        hf_token=hf_token,
        # common
        temperature=temperature,
        max_new_tokens=max_new_tokens,
        top_k=top_k,
    )

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("در حال نوشتن پاسخ…")

        t0 = time.time()
        try:
            result = generate_answer(prompt, **cfg) or {}
        except Exception as e:
            result = {"intro": "", "core": f"خطا: {e}", "outro": ""}

        dt = time.time() - t0

        # مونتاژ پاسخ سه‌بخشی به یک پیام واحد
        intro = (result.get("intro") or "").strip()
        core = (result.get("core") or "").strip()
        outro = (result.get("outro") or "").strip()

        parts = []
        if intro:
            parts.append(f"**مقدمه**\n\n{intro}")
        if core:
            parts.append(f"**هستهٔ پاسخ**\n\n{core}")
        if outro:
            parts.append(f"**جمع‌بندی**\n\n{outro}")
        final_md = "\n\n---\n\n".join(parts) if parts else "پاسخی دریافت نشد."

        placeholder.markdown(final_md)
        st.caption(f"⏱️ زمان تولید: {dt:.2f}s")

    # 3) ذخیرهٔ پیام دستیار در تاریخچه
    st.session_state.messages.append({"role": "assistant", "content": final_md})
