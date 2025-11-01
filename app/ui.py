#FEYZ
#DEO
import streamlit as st
import requests
import time

# ====== تنظیمات اولیه صفحه ======
st.set_page_config(
    page_title="منتور شخصی امین",
    page_icon="🌿",
    layout="centered"
)

# ====== استایل اختصاصی ======
st.markdown("""
    <style>
        body {
            background-color: #f8f9fa;
        }
        .main-title {
            font-size: 2.1rem;
            font-weight: 700;
            color: #2c3e50;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        .subtitle {
            text-align: center;
            color: #6c757d;
            margin-bottom: 2rem;
            font-size: 1rem;
        }
        .prompt-box {
            border: 1px solid #e1e1e1;
            border-radius: 12px;
            padding: 0.8rem 1rem;
            background-color: #ffffff;
        }
        .quick-prompts {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-bottom: 1.5rem;
        }
        .quick-btn {
            background-color: #e9f5ff;
            color: #0078d7;
            border: none;
            border-radius: 10px;
            padding: 0.5rem 0.8rem;
            cursor: pointer;
            transition: 0.2s;
        }
        .quick-btn:hover {
            background-color: #0078d7;
            color: white;
        }
        .response-box {
            margin-top: 1rem;
            padding: 1rem;
            background-color: #f1f3f4;
            border-radius: 10px;
            border-left: 5px solid #0078d7;
        }
    </style>
""", unsafe_allow_html=True)

# ====== عنوان و توضیح ======
st.markdown('<div class="main-title">منتور شخصی امین</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">همراه هوشمند شما در مسیر رشد، یادگیری و تصمیم‌گیری</div>', unsafe_allow_html=True)

# ====== پیشنهاد سؤالات آماده ======
col1, col2, col3 = st.columns(3)
prompts = [
    "چطور می‌تونم مهارت مذاکره‌م رو بهتر کنم؟",
    "یه مسیر یادگیری برای هوش مصنوعی پیشنهاد بده.",
    "چطور در تصمیم‌گیری‌هام منطقی‌تر عمل کنم؟"
]
selected_prompt = None
with col1:
    if st.button(prompts[0], key="q1"):
        selected_prompt = prompts[0]
with col2:
    if st.button(prompts[1], key="q2"):
        selected_prompt = prompts[1]
with col3:
    if st.button(prompts[2], key="q3"):
        selected_prompt = prompts[2]

# ====== فیلد ورودی ======
user_input = st.text_area("✍️ بنویس:", value=selected_prompt or "", placeholder="سؤال یا موضوعت رو بنویس...")

# ====== ارسال درخواست ======
if st.button("ارسال 🔹", use_container_width=True):
    if user_input.strip():
        with st.spinner("منتور در حال فکر کردنه 💭..."):
            time.sleep(1.2)  # شبیه‌سازی پردازش

            # اینجا بعداً به API واقعی وصل می‌کنی
            response = f"""
            🔸 خلاصه:
            تمرکز کن روی درک نیاز طرف مقابل پیش از پاسخ دادن.

            🔹 توضیح:
            مذاکره مؤثر یعنی گوش دادن فعال و تحلیل انگیزه‌ها. سعی کن قبل از هر پیشنهاد، با سؤالات باز احساس و هدف فرد مقابل رو بفهمی.

            🔹 پیشنهاد عملی:
            تمرین کن هر روز با یکی از هم‌تیمی‌هات گفت‌وگو رو با یک سؤال درک‌محور شروع کنی.

            🔹 نتیجه:
            درک، پایهٔ تمام روابط مؤثره. می‌خوای همین مسیر رو باهم ادامه بدیم؟
            """

            st.markdown(f'<div class="response-box">{response}</div>', unsafe_allow_html=True)
    else:
        st.warning("لطفاً قبل از ارسال، یک سؤال بنویس.")

# ====== پانوشت ======
st.markdown("---")
st.caption("🌿 ساخته شده با عشق در مؤسسه آموزش عالی آزاد امین")

#FEYZ
#DEO
