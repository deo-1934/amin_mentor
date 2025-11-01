#FEYZ
#DEO
import streamlit as st
from app.generator import generate_answer

# -------------------------
# تنظیمات صفحه
# -------------------------
st.set_page_config(page_title="منتور شخصی امین", page_icon="🧠", layout="centered")

st.title("🧠 منتور شخصی امین")
st.caption("یک دوست  در کنارت 💬")

# -------------------------
# حافظه مکالمه در session_state
# -------------------------
if "chat_history" not in st.session_state:
    # هر آیتم در این لیست شامل نقش و محتواست
    st.session_state.chat_history = []

# -------------------------
# دکمه شروع گفت‌وگوی جدید
# -------------------------
if st.button("🔄 شروع گفت‌وگوی جدید"):
    st.session_state.chat_history = []
    st.success("✅ گفت‌وگوی جدید شروع شد")

st.write("")  # فاصلهٔ ظاهری

# -------------------------
# نمایش مکالمات قبلی
# -------------------------
for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        st.markdown(f"🧍‍♀️ **تو:** {msg['content']}")
    else:
        st.markdown(f"🤖 **منتور:** {msg['content']}")
    st.divider()

# -------------------------
# ورودی چت
# -------------------------
user_input = st.chat_input("سؤالت رو بنویس یا حرف دلت رو بزن...")

if user_input:
    # ۱. پیام کاربر رو ذخیره کن و نشون بده
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    st.markdown(f"🧍‍♀️ **تو:** {user_input}")
    st.divider()

    # ۲. ساخت context از کل گفتگو (کاربر + منتور)
    context_chunks = [
        f"{msg['role']}: {msg['content']}" for msg in st.session_state.chat_history
    ]

    # ۳. تماس با مدل
    with st.spinner("منتور داره فکر می‌کنه… 🤔"):
        try:
            answer = generate_answer(user_input, context_chunks)
        except Exception as e:
            answer = f"⚠️ خطا در پاسخ‌گویی: {e}"

    # ۴. نمایش و ذخیرهٔ پاسخ منتور
    st.session_state.chat_history.append({"role": "assistant", "content": answer})
    st.markdown(f"🤖 **منتور:** {answer}")
    st.divider()

#FEYZ
#DEO
