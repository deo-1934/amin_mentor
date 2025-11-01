import streamlit as st
from app.generator import generate_answer
from datetime import datetime

# -------------------------
# تنظیمات صفحه
# -------------------------
st.set_page_config(
    page_title="منتور شخصی امین",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# -------------------------
# توابع کمکی
# -------------------------
def clear_chat_history():
    """پاک کردن تاریخچه چت"""
    st.session_state.chat_history = []
    st.rerun()

def display_message(role: str, content: str):
    """نمایش پیام با فرمت مناسب"""
    avatar = "🧍‍♀️" if role == "user" else "🤖"
    with st.chat_message(role):
        st.markdown(f"**{avatar} {role.capitalize()}:** {content}")

def get_context() -> list[str]:
    """استخراج متن پاسخ‌های قبلی منتور برای استفاده به عنوان context"""
    return [
        msg["content"]
        for msg in st.session_state.chat_history
        if msg["role"] == "assistant"
    ]

# -------------------------
# تنظیمات اولیه
# -------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# -------------------------
# رابط کاربری
# -------------------------
st.title("🧠 منتور شخصی امین")
st.caption("یک دوست عاقل و کنار تو 💬")

# دکمه پاک کردن تاریخچه چت
st.button(
    "🔄 شروع گفت‌وگوی جدید",
    on_click=clear_chat_history,
    use_container_width=True,
    type="primary"
)

# نمایش تاریخچه چت
for msg in st.session_state.chat_history:
    display_message(msg["role"], msg["content"])

# دریافت ورودی کاربر
if user_input := st.chat_input("پیام خود را اینجا تایپ کنید..."):
    # ثبت و نمایش پیام کاربر
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    display_message("user", user_input)

    # دریافت پاسخ از منتور
    with st.spinner("منتور در حال فکر کردن..."):
        try:
            context = get_context()
            answer = generate_answer(user_input, context)
        except Exception as e:
            answer = f"⚠️ خطا در دریافت پاسخ: {str(e)}"

    # ثبت و نمایش پاسخ منتور
    st.session_state.chat_history.append({"role": "assistant", "content": answer})
    display_message("assistant", answer)

# -------------------------
# اطلاعات اضافی (اختیاری)
# -------------------------
with st.expander("⚙️ اطلاعات بیشتر"):
    st.write("""
    **منتور شخصی امین** یک دستیار هوشمند است که به سوالات شما پاسخ می‌دهد.
    - برای شروع یک گفت‌وگوی جدید، روی دکمه "شروع گفت‌وگوی جدید" کلیک کنید.
    - تاریخچه چت در حافظه موقت ذخیره می‌شود و با بستن صفحه پاک می‌شود.
    """)
