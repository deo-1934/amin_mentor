#FEYZ
#DEO
# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from typing import List, Dict, Any
import streamlit as st

# -------------------------------------------------
# اطمینان از اینکه پایتون می‌تونه پکیج app رو پیدا کنه
# (برای جلوگیری از ModuleNotFoundError روی Streamlit Cloud)
# -------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.generator import generate_answer
from app import retriever

# -------------------------------------------------
# تنظیمات کلی صفحه
# -------------------------------------------------
st.set_page_config(
    page_title="Amin Mentor",
    page_icon="💬",
    layout="centered",
)

# نگهداری تاریخچه مکالمه در session_state
# هر آیتم داخل history به شکل:
# {"role": "user" | "assistant", "content": "متن پیام"}
if "history" not in st.session_state:
    st.session_state.history: List[Dict[str, Any]] = []

# هدر رابط
st.title("Amin Mentor")

# نمایش تاریخچه چت تا این لحظه
# streamlit.chat_message خودش حباب می‌سازه (user, assistant)
for turn in st.session_state.history:
    with st.chat_message("user" if turn["role"] == "user" else "assistant"):
        st.markdown(turn["content"])

#DEO
def _append(role: str, content: str):
    """یک پیام جدید به هیستوری اضافه کن"""
    st.session_state.history.append({"role": role, "content": content})


# فرم ورودی (پیام جدید کاربر)
with st.form("chat_form", clear_on_submit=True):
    user_msg = st.text_area(
        "پیامت رو بنویس:",
        height=120,
        placeholder="سلام! از من هر چیزی در مورد کسب‌وکار، استراتژی، اولویت‌بندی کار یا مسیر حرکت بپرس...",
    )
    submitted = st.form_submit_button("بفرست")


# فقط وقتی فرم ارسال شد و متن خالی نباشه
if submitted and user_msg.strip():
    user_text = user_msg.strip()

    # ۱. پیام کاربر رو به تاریخچه اضافه کن (برای اینکه روی صفحه هم بلافاصله نشون داده بشه)
    _append("user", user_text)

    # ۲. ساخت context محلی (دانش داخلی پروژه)
    #    سعی می‌کنیم تکه‌های مرتبط از دیتای داخلی بیاریم
    ctx_items: List[str] = []
    try:
        retrieved = retriever.retrieve(user_text, top_k=4)
        # هر آیتم retriever معمولاً شبیه {"text": "...", "score": 0.88, "source": "file.txt[chunk:3]"}
        ctx_items = [
            f"{r.get('text','')}\n(منبع: {r.get('source','?')})"
            for r in retrieved
        ][:4]
    except Exception:
        # اگه retriever خطا بده، نذار کل سیستم بترکه
        ctx_items = []

    # ۳. ساخت حافظه مکالمه
    #    ما آخرین چند پیام رو به مدل پاس می‌دیم، تا بفهمه «ادامه بده» یعنی ادامه چی.
    #    برای اینکه هزینه نجومی نشه، فقط آخرین 6 پیام (user+assistant) رو پاس می‌دیم.
    conversation_memory_lines: List[str] = []
    for turn in st.session_state.history[-6:]:
        role_label = "کاربر" if turn["role"] == "user" else "منتور"
        # نقش رو صریح می‌گیم که مدل بفهمه چه کسی چی گفته
        conversation_memory_lines.append(f"{role_label}: {turn['content']}")

    conversation_memory_block = "\n".join(conversation_memory_lines).strip()

    # ۴. کانتکست نهایی که به مدل می‌دیم
    #    اول حافظه مکالمه، بعد دانش داخلی (retriever)
    #    این می‌ره داخل generator.generate_answer ، که adaptive routing داره
    full_context: List[str] = []
    if conversation_memory_block:
        full_context.append(
            "گفتگو تا اینجا:\n" + conversation_memory_block
        )
    # دانش دامنه‌ای مثل مذاکره، استراتژی، کار روی مشتری و ... :
    full_context.extend(ctx_items)

    # ۵. تولید پاسخ
    with st.spinner("در حال فکر کردن..."):
        try:
            answer_text = generate_answer(
                query=user_text,
                context=full_context
            )
        except Exception:
            # اگر generator یا مدل بیرونی خطا بده، یه پیام محترمانه و کوتاه نشون بده
            answer_text = (
                "الان نتونستم مطمئن جواب بدم. یک بار دیگه بپرس یا یه کم واضح‌تر بگو دقیقا دنبال چی هستی 🙏"
            )

    # ۶. پاسخ رو تو تاریخچه ذخیره کن
    _append("assistant", answer_text)

    # ۷. و روی صفحه نشون بده (حباب دستیار)
    with st.chat_message("assistant"):
        st.markdown(answer_text)
