
#FEYZ
#DEO
import streamlit as st
from .generator import generate_answer  # ایمپورت نسبی، این مهمه 👈

# -------------------------
# تنظیمات اولیه‌ی صفحه
# -------------------------
st.set_page_config(page_title="Amin Mentor", page_icon="🧠", layout="centered")

st.title("🧠 منتور شخصی امین")
st.caption("یک دوست عاقل و کنار تو 💬")

# -------------------------
# حافظه مکالمه در session_state
# -------------------------
if "chat_history" not in st.session_state:
    # هر آیتم می‌شه {"role": "user" یا "assistant", "content": "متن"}
    st.session_state.chat_history = []

# -------------------------
# تابع نمایش پیام‌ها
# -------------------------
def render_messages():
    for msg in st.session_state.chat_history:
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            st.markdown(f"🧍‍♀️ **تو:** {content}")
        else:
            st.markdown(f"🤖 **منتور:** {content}")

        st.divider()

# پیام‌های قبلی رو نشون بده
render_messages()

# -------------------------
# ورودی چت
# -------------------------
user_input = st.chat_input("هرچی تو ذهنته همینجا بگو...")

if user_input:
    # 1. پیام کاربر رو ذخیره و نمایش بده
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    st.markdown(f"🧍‍♀️ **تو:** {user_input}")
    st.divider()

    # 2. زمینه برای مدل:
    # ما الان فقط پاسخ‌های قبلی منتور رو به عنوان context می‌فرستیم
    # (ساده و کم‌هزینه. بعدا می‌تونیم گفت‌وگو رو کامل بفرستیم)
    context_chunks = [
        msg["content"]
        for msg in st.session_state.chat_history
        if msg["role"] == "assistant"
    ]

    # 3. تولید جواب
    with st.spinner("منتور داره فکر می‌کنه… 🤔"):
        try:
            answer = generate_answer(
                user_question=user_input,
                context=context_chunks,
            )
        except Exception as e:
            answer = f"⚠️ یه خطا پیش اومد: {e}"

    # 4. جواب منتور رو ذخیره و نمایش بده
    st.session_state.chat_history.append({"role": "assistant", "content": answer})
    st.markdown(f"🤖 **منتور:** {answer}")
    st.divider()

# -------------------------
# ریست مکالمه
# -------------------------
if st.button("🔄 شروع گفت‌وگوی جدید"):
    st.session_state.chat_history = []
    st.experimental_rerun()

#FEYZ
#DEO
