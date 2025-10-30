import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from app.retriever import retrieve
from app.generator import generate_answer

# پیکربندی صفحه
st.set_page_config(
    page_title="Amin Mentor",
    page_icon="💬",
)

# هدر بالا
st.title("Amin Mentor")
st.caption("یه سؤال بپرس؛ من از دانش داخلی امین جواب می‌سازم.")

# --- فرم چت با یک ورودی و یک دکمه ---
with st.form("chat"):
    q = st.text_input(
        "سؤال شما:",
        value="مثلاً: اصول مذاکره برد-برد چیست؟",
        placeholder="هر چیزی که می‌خوای بدونی رو بپرس..."
    )

    submitted = st.form_submit_button("ارسال")

# مقادیر داخلی که دیگه به کاربر نشون نمی‌دیم
TOP_K_DEFAULT = 5
MAX_NEW_TOKENS_DEFAULT = 200

if submitted and q.strip():
    # ۱. مرحله بازیابی
    with st.spinner("در حال جستجوی منابع داخلی..."):
        hits = retrieve(q, top_k=TOP_K_DEFAULT)

    # نمایش منابع بازیابی‌شده
    if hits:
        st.subheader("📚 منابع پیدا شده")
        for i, h in enumerate(hits, 1):
            st.markdown(f"**منبع {i}**")
            st.write(h.get("text", ""))

            # نمایش اطلاعات منبع (اختیاری)
            src = h.get("source") or {}
            if src:
                meta_bits = []
                if "file" in src:
                    meta_bits.append(f"فایل: {src['file']}")
                if "chunk_idx" in src:
                    meta_bits.append(f"بخش: {src['chunk_idx']}")
                if meta_bits:
                    st.caption(" / ".join(meta_bits))

            st.divider()
    else:
        st.info("هیچ بخشی از دانش داخلی پیدا نشد.")

    # ۲. مرحله تولید پاسخ
    ctx = [h["text"] for h in hits if h.get("text")]
    with st.spinner("در حال تولید پاسخ..."):
        ans = generate_answer(
            q,
            context=ctx,
            max_new_tokens=MAX_NEW_TOKENS_DEFAULT
        )

    st.subheader("🧠 پاسخ منتور")
    st.write(ans)

    # ۳. باکس فنی فقط برای تو (می‌تونی کامل حذفش کنی اگه نخوای)
    st.markdown("---")
    with st.expander("جزئیات فنی (برای توسعه‌دهنده)"):
        st.json({
            "query": q,
            "top_k_used": TOP_K_DEFAULT,
            "context_snippets_used": len(ctx),
            "raw_context_preview": ctx[:2],  # فقط ۲ تا، برای امنیت
        })
