# app/ui.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from app.retriever import retrieve
from app.generator import generate_answer

# پیکربندی صفحه
st.set_page_config(page_title="Amin Mentor", page_icon="💬")

# هدر
st.title("Amin Mentor")
st.caption("سؤال‌تان را بپرسید؛ من از دانش داخلی امین پاسخ می‌سازم.")

# فرم
with st.form("chat"):
    q = st.text_input(
        "سؤال شما:",
        value="مثلاً: اصول مذاکره برد-برد چیست؟",
        placeholder="هر چیزی که می‌خوای بدونی رو بپرس..."
    )
    show_sources = st.checkbox("نمایش منابع بازیابی‌شده", value=False)
    submitted = st.form_submit_button("ارسال")

# تنظیمات داخلی
TOP_K_DEFAULT = 5
MAX_NEW_TOKENS_DEFAULT = 200

if submitted and q.strip():
    with st.spinner("در حال آماده‌سازی پاسخ..."):
        # ۱) بازیابی
        hits = retrieve(q, top_k=TOP_K_DEFAULT)
        context = [h.get("text", "") for h in hits if h.get("text")]

        # ۲) تولید پاسخ
        answer = generate_answer(
            q,
            context=context,
            max_new_tokens=MAX_NEW_TOKENS_DEFAULT
        )

    # فقط پاسخ
    st.subheader("🧠 پاسخ منتور")
    st.write(answer)

    # نمایش منابع در صورت درخواست
    if show_sources:
        st.markdown("---")
        st.subheader("📚 منابع")
        if not hits:
            st.info("منبعی یافت نشد.")
        else:
            for i, h in enumerate(hits, start=1):
                st.markdown(f"**منبع {i}**")
                st.write(h.get("text", ""))
                src = h.get("source") or {}
                meta_bits = []
                if "file" in src:
                    meta_bits.append(f"فایل: {src['file']}")
                if "chunk_idx" in src:
                    meta_bits.append(f"بخش: {src['chunk_idx']}")
                if meta_bits:
                    st.caption(" / ".join(meta_bits))
                st.divider()
