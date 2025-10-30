# app/ui.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from app.retriever import retrieve
from app.generator import generate_hybrid_answer, healthcheck


st.set_page_config(
    page_title="Amin Mentor",
    page_icon="🎓",
)

st.markdown(
    """
    <style>
    .main-title {
        font-size: 2rem;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .subtext {
        color: #aaa;
        font-size: 0.9rem;
        line-height: 1.6;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="main-title">🎓 Amin Mentor</div>
    <div class="subtext">
    اینجا منتور شخصی امینه. ازت حمایت می‌کنه، بهت راه‌حل قابل‌اجرا می‌ده،
    و سعی می‌کنه با لحن انسانی جواب بده. 👇
    </div>
    """,
    unsafe_allow_html=True,
)

user_q = st.text_input("سوالت رو بنویس 👇", placeholder="مثلاً: چطور تو مذاکره استرس نداشته باشم؟")

col1, col2 = st.columns([1,1])
with col1:
    ask_btn = st.button("پرسیدن از منتور 🧠", use_container_width=True)
with col2:
    debug_toggle = st.toggle("نمایش جزییات فنی (برای توسعه‌دهنده)", value=False)

if ask_btn and user_q.strip():
    with st.spinner("در حال فکر کردن... ⏳"):
        # مرحله ۱: بازیابی دانش داخلی (RAG)
        hits = retrieve(user_q, top_k=5)

        # مرحله ۲: ترکیب با مدل زبانی برای پاسخ انسانی
        final_answer = generate_hybrid_answer(
            user_question=user_q,
            retrieved_docs=hits,
            max_new_tokens=200,
        )

    # نمایش فقط جواب نهایی برای کاربر
    st.subheader("پاسخ منتور 💬")
    st.write(final_answer)

    # اگر تیک debug خورده بود، اطلاعات فنی رو هم نشون بده
    if debug_toggle:
        st.markdown("---")
        st.write("### 📚 منابعی که پیدا شد")
        if hits:
            for i, h in enumerate(hits, start=1):
                st.markdown(f"**منبع {i}:** {h.get('text','')}")
                st.caption(f"📎 {h.get('source','?')} | distance={h.get('distance','?')}")
        else:
            st.write("هیچ منبع مستقیمی پیدا نشد.")

        st.markdown("---")
        st.write("### 🔧 وضعیت مدل (healthcheck):")
        st.json(healthcheck())

elif ask_btn and not user_q.strip():
    st.error("یه سوال بنویس بعد بزن روی دکمه 😅")
