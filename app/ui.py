# app/ui.py
import sys
import os
import streamlit as st

# ------------------------------------------------------------
# مسیر پروژه را به sys.path اضافه می‌کنیم تا در Cloud ایمپورت‌ها بشناسد
# ------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ------------------------------------------------------------
# ایمپورت‌های حساس با لاگ برای دیباگ Cloud
# ------------------------------------------------------------
try:
    from app.retriever import retrieve
except Exception as e:
    st.error(f"❌ retriever import error: {e}")

try:
    from app.generator import generate_answer
except Exception as e:
    st.error(f"❌ generator import error: {e}")

# ------------------------------------------------------------
# تنظیمات صفحه
# ------------------------------------------------------------
st.set_page_config(page_title="Amin Mentor", page_icon="💬")

st.title("🎓 Amin Mentor")

st.markdown("""
به **منتور شخصی امین** خوش اومدی!  
اینجا می‌تونی پرسش‌هات درباره‌ی کسب‌وکار، یادگیری، و توسعه فردی رو بپرسی 💬  
و از هوش مصنوعی منتور، پاسخ تخصصی و شخصی‌سازی‌شده بگیری.
""")

# ------------------------------------------------------------
# ورودی کاربر
# ------------------------------------------------------------
query = st.text_input("سؤال خودت رو بنویس 👇")

if st.button("پرسیدن از منتور 🧠") and query:
    with st.spinner("در حال پردازش پاسخ منتور..."):
        try:
            # داده‌های بازیابی شده از حافظه یا پایگاه دانش
            retrieved_docs = retrieve(query)
            st.markdown("### 📚 منابع پیدا شده:")
            for i, doc in enumerate(retrieved_docs, start=1):
                st.markdown(f"**منبع {i}:** {doc}")

            # پاسخ نهایی منتور
            answer = generate_answer(query, retrieved_docs)
            st.markdown("### 💬 پاسخ منتور:")
            st.write(answer)

        except Exception as e:
            st.error(f"🚨 خطایی رخ داد: {e}")
else:
    st.info("👆 یه سؤال بنویس و روی دکمه‌ی بالا بزن تا پاسخ منتور رو ببینی.")

# ------------------------------------------------------------
# اطلاعات فنی برای توسعه‌دهنده (اختیاری)
# ------------------------------------------------------------
with st.expander("⚙️ جزئیات فنی (برای توسعه‌دهنده‌ها)"):
    st.json({
        "cwd": os.getcwd(),
        "sys.path": sys.path[:3],
        "file": __file__,
        "project_root": PROJECT_ROOT,
    })
