#FEYZ
#DEO
import streamlit as st
from app.generator import generate_answer

# -------------------------
# تنظیمات اولیه‌ی صفحه
# -------------------------
st.set_page_config(page_title="Amin Mentor", page_icon="🧠", layout="centered")

st.title("🧠 منتور شخصی امین")
st.caption("دوست عاقل، صبور و همیشه در کنارت 💬")

# -------------------------
# حافظه مکالمه در session_state
# -------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # لیست از {"role": "user"/"assistant", "content": str}

# -------------------------
# تابع برای نمایش پیام‌ها
# -------------------------
def render_messages():
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f"🧍‍♀️ **تو:** {msg['content']}")
        else:
            st.markdown(f"🤖 **منتور:** {msg['content']}")
        st.divider()

# -------------------------
# نمایش تاریخچه‌ی قبلی
# -------------------------
render_messages()

# -------------------------
# ورودی کاربر
# -------------------------
user_input = st.chat_input("سؤالت رو بنویس...")

if user_input:
    # افزودن پیام کاربر به حافظه
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    st.markdown(f"🧍‍♀️ **تو:** {user_input}")
    st.divider()

    # ساخت زمینه (context) از همه پاسخ‌های قبلی
    context = [msg["content"] for msg in st.session_state.chat_history if msg["role"] == "assistant"]

    # گرفتن پاسخ از مدل
    with st.spinner("منتور در حال فکر کردن... 🤔"):
        try:
            answer = generate_answer(user_input, context)
        except Exception as e:
            answer = f"⚠️ خطا در پاسخ‌گویی: {e}"

    # نمایش و ذخیره پاسخ
    st.session_state.chat_history.append({"role": "assistant", "content": answer})
    st.markdown(f"🤖 **منتور:** {answer}")
    st.divider()

# -------------------------
# دکمه پاک‌سازی گفتگو
# -------------------------
if st.button("🔄 شروع گفت‌وگوی جدید"):
    st.session_state.chat_history = []
    st.experimental_rerun()
#FEYZ
#DEO
