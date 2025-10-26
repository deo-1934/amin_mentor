import sys
import os
import streamlit as st

# ✅ مسیر پوشه اصلی پروژه رو به sys.path اضافه می‌کنیم تا importها درست کار کنن
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ✅ حالا می‌تونیم ماژول‌های داخل app رو به درستی import کنیم
from app.retriever import retrieve

st.set_page_config(page_title="Amin Mentor", layout="wide")

st.title("🧠 Amin Mentor - Your AI Personal Assistant")
st.markdown("---")

# UI: ورودی کاربر
user_input = st.text_area("سؤال خود را وارد کنید:", height=120)

# دکمه اجرا
if st.button("🔍 جستجو و پاسخ"):
    if user_input.strip():
        with st.spinner("در حال بازیابی پاسخ..."):
            try:
                result = retrieve(user_input)
                st.success("✅ پاسخ:")
                st.write(result)
            except Exception as e:
                st.error(f"❌ خطا در پردازش: {e}")
    else:
        st.warning("لطفاً ابتدا متنی وارد کنید.")

# Footer
st.markdown("---")
st.caption("⚙️ Developed by Amin Mentor AI System")
