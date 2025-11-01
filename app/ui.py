#FEYZ
#DEO
import os
import sys
import streamlit as st

# -------------------------
# افزودن مسیر پکیج به sys.path
# -------------------------
# مسیر فولدر بالاتر از پوشه app (یعنی amin_mentor)
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

# حالا می‌تونیم با خیال راحت generator رو import کنیم
from app.generator import generate_answer

# -------------------------
# تنظیمات صفحه
# -------------------------
st.set_page_config(page_title="منتور شخصی امین", page_icon="🧠", layout="centered")

st.title("🧠 منتور شخصی امین")
st.caption("یک دوست عاقل، صبور و همیشه در کنارت 💬")

# -------------------------
# حافظه مکالمه در session_state
# -------------------------
if "chat_history" not in st.session_state:
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
    # پیام کاربر
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    st.markdown(f"🧍‍♀️ **تو:** {user_input}")
    st.divider()

    # کل گفت‌وگو (user + assistant) برای context
    context_chunks = [
        f"{msg['role']}: {msg['content']}" for msg in st.session_state.chat_history
    ]

    # پاسخ مدل
    with st.spinner("منتور داره فکر می‌کنه… 🤔"):
        try:
            answer = generate_answer(user_input, context_chunks)
        except Exception as e:
            answer = f"⚠️ خطا در پاسخ‌گویی: {e}"

    # ذخیره پاسخ و نمایش
    st.session_state.chat_history.append({"role": "assistant", "content": answer})
    st.markdown(f"🤖 **منتور:** {answer}")
    st.divider()

#FEYZ
#DEO
