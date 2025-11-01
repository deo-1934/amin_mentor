#FEYZ
#DEO
# -*- coding: utf-8 -*-
import os
import json
import time
from typing import Dict, Any

import streamlit as st

try:
    from app.generator import generate_answer, load_settings
except Exception:
    from generator import generate_answer, load_settings

st.set_page_config(page_title="Amin Mentor", page_icon="🤝", layout="wide")

st.markdown("### منتور شخصی امین\nپاسخ سه‌بخشی: مقدمه، هسته، جمع‌بندی.")

col_left, col_right = st.columns([2, 1], gap="large")
settings = load_settings()

with col_left:
    st.subheader("سؤال شما")
    user_query = st.text_area(
        "متن سؤال:",
        placeholder="مثلاً: چطور با کمترین هزینه API رو وصل کنم؟",
        height=160
    )

    with st.expander("تنظیمات پیشرفته", expanded=False):
        provider_options = ["openai", "huggingface", "offline"]
        try:
            default_idx = provider_options.index(settings.get("MODEL_PROVIDER", "openai"))
        except ValueError:
            default_idx = 0
        model_provider = st.selectbox("Model Provider:", options=provider_options, index=default_idx)

        # OpenAI fields
        openai_model = st.text_input(
            "OPENAI_MODEL",
            value=settings.get("OPENAI_MODEL", "gpt-4o-mini"),
            placeholder="gpt-4o-mini / gpt-4.1-mini / ...",
            help="اگر Provider=openai باشد"
        )
        openai_api_key = st.text_input(
            "OPENAI_API_KEY",
            value=settings.get("OPENAI_API_KEY", ""),
            type="password",
            help="در Secrets ست شده باشد بهتر است"
        )

        # HF fields
        model_endpoint = st.text_input(
            "MODEL_ENDPOINT (HuggingFace)",
            value=settings.get("MODEL_ENDPOINT", ""),
            placeholder="https://api-inference.huggingface.co/models/gpt2",
            help="اگر Provider=huggingface باشد"
        )
        hf_token = st.text_input(
            "HF_TOKEN",
            value=settings.get("HF_TOKEN", ""),
            type="password"
        )

        temperature = st.slider("Temperature", 0.0, 1.5, value=0.2, step=0.05)
        max_new_tokens = st.slider("Max new tokens", 16, 1024, value=256, step=16)
        top_k = st.slider("Top-K Retrieval", 1, 10, value=5, step=1)
        show_raw = st.checkbox("نمایش خروجی خام (Debug)", value=False)

    ask = st.button("🚀 بپرس", use_container_width=True)

#DEO
with col_right:
    st.subheader("وضعیت سیستم")
    st.code(json.dumps({
        "provider": settings.get("MODEL_PROVIDER"),
        "has_openai_key": bool(settings.get("OPENAI_API_KEY")),
        "has_hf_token": bool(settings.get("HF_TOKEN")),
        "cache_path": settings.get("CACHE_PATH"),
    }, ensure_ascii=False, indent=2))
    st.info("اگر از OpenAI استفاده می‌کنی، OPENAI_API_KEY را در Secrets بگذار.", icon="ℹ️")

if ask:
    if not user_query.strip():
        st.warning("اول سؤال را بنویس.", icon="⚠️")
    else:
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
        t0 = time.time()
        with st.spinner("در حال تولید پاسخ..."):
            try:
                result = generate_answer(user_query, **cfg)
            except Exception as e:
                st.error(f"خطا در تولید پاسخ: {e}")
                result = None
        dt = time.time() - t0

        if result is not None:
            st.success(f"✅ آماده شد (زمان: {dt:.2f}s)")
            st.markdown("#### مقدمه"); st.write(result.get("intro", ""))
            st.markdown("#### هستهٔ پاسخ"); st.write(result.get("core", ""))
            st.markdown("#### جمع‌بندی"); st.write(result.get("outro", ""))

            if show_raw:
                st.markdown("#### RAW")
                st.code(json.dumps(result, ensure_ascii=False, indent=2))
