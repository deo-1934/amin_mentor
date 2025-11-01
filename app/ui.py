#FEYZ
#DEO
# -*- coding: utf-8 -*-
import json
import time
from typing import Dict, Any, List

import streamlit as st

# تلاش برای ایمپورت به هر دو حالت اجرا (داخل پکیج/مستقل)
try:
    from app.generator import generate_answer, load_settings
except Exception:
    from generator import generate_answer, load_settings

st.set_page_config(page_title="Amin Mentor — Chat", page_icon="🤝", layout="wide")

# هدر مینیمال
st.markdown("## منتور شخصی امین")
st.caption("چت تمیز و سریع؛ پاسخ‌ها به شکل **مقدمه / هسته / جمع‌بندی** نمایش داده می‌شوند.")

# تنظیمات از Secrets/ENV (بدون نمایش)
settings = load_settings()
provider_default = settings.get("MODEL_PROVIDER", "openai")
openai_model_default = settings.get("OPENAI_MODEL", "gpt-4o-mini")
openai_key_default = settings.get("OPENAI_API_KEY", "")
hf_endpoint_default = settings.get("MODEL_ENDPOINT", "")
hf_token_default = settings.get("HF_TOKEN", "")

#DEO
# حالت ادمین اختیاری (فقط اگر ?admin=1 به URL اضافه شود)
is_admin = False
try:
    # Streamlit v1.31+: st.query_params به صورت dict-like
    qp = st.query_params  # type: ignore[attr-defined]
    is_admin = str(qp.get("admin", "0")) in ("1", "true", "True")
except Exception:
    pass

if is_admin:
    with st.expander("⚙️ Admin (پنهان از کاربر نهایی)", expanded=False):
        st.code(json.dumps({
            "provider": provider_default,
            "has_openai_key": bool(openai_key_default),
            "has_hf_token": bool(hf_token_default),
            "cache_path": settings.get("CACHE_PATH"),
        }, ensure_ascii=False, indent=2))

# پارامترهای ثابت UI (نمایش نمی‌دهیم؛ فقط استفاده می‌کنیم)
TEMPERATURE_DEFAULT = 0.2
MAX_NEW_TOKENS_DEFAULT = 256
TOP_K_DEFAULT = 5

# نگهداری تاریخچهٔ چت
if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, str]] = []

# نمایش تاریخچه
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ورودی چت
prompt = st.chat_input("پیام خود را بنویسید…")
if prompt:
    # پیام کاربر
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # فراخوانی ژنراتور با مقادیر از Secrets/ENV
    cfg: Dict[str, Any] = dict(
        model_provider=provider_default,
        # OpenAI
        openai_model=openai_model_default,
        openai_api_key=openai_key_default,
        # HF
        model_endpoint=hf_endpoint_default,
        hf_token=hf_token_default,
        # Common
        temperature=TEMPERATURE_DEFAULT,
        max_new_tokens=MAX_NEW_TOKENS_DEFAULT,
        top_k=TOP_K_DEFAULT,
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

    # ذخیره پاسخ
    st.session_state.messages.append({"role": "assistant", "content": final_md})
