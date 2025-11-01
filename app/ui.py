#FEYZ
#DEO
import streamlit as st
import json
import requests

# تنظیمات اولیه صفحه
st.set_page_config(
    page_title="منتور شخصی امین",
    page_icon="🎓",
    layout="centered"
)

# استایل سفارشی (حرفه‌ای و رسمی)
st.markdown("""
    <style>
        body {
            direction: rtl;
            text-align: right;
            font-family: 'Vazirmatn', sans-serif;
            background-color: #0E1117;
            color: #EDEDED;
        }
        .stTextInput textarea {
            direction: rtl;
            text-align: right;
        }
        .mentor-box {
            border: 1px solid #30363D;
            border-radius: 12px;
            background-color: #161B22;
            padding: 20px;
            margin-top: 10px;
        }
        .mentor-header {
            font-weight: bold;
            color: #58A6FF;
            margin-bottom: 10px;
        }
        .mentor-intro {
            color: #D2D2D2;
            margin-bottom: 6px;
        }
        .mentor-core {
            color: #FFFFFF;
            margin-bottom: 6px;
        }
        .mentor-outro {
            color: #A0A0A0;
            font-style: italic;
        }
    </style>
""", unsafe_allow_html=True)

# عنوان بالای صفحه
st.markdown("<h3 style='text-align:center; color:#58A6FF;'>منتور شخصی امین 🎓</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#AAAAAA;'>همراه هوشمند شما در مسیر رشد، یادگیری و تصمیم‌گیری</p>", unsafe_allow_html=True)

# گزینه‌های آماده (پیشنهاد پرسش)
cols = st.columns(3)
cols[0].button("چطور در تصمیم‌گیری‌هام منطقی‌تر عمل کنم؟")
cols[1].button("به مسیر یادگیری برای هوش مصنوعی پیشنهاد بده")
cols[2].button("چطور می‌تونم مهارت خلاقیت خودم رو بهتر کنم؟")

# ورودی کاربر
user_input = st.text_area("پرسش یا دغدغه‌ی خود را بنویسید:", placeholder="مثلاً: چطور تمرکز خودم را هنگام مطالعه حفظ کنم؟")

# دکمه ارسال
if st.button("ارسال"):
    if not user_input.strip():
        st.warning("لطفاً ابتدا پرسش خود را بنویسید.")
    else:
        with st.spinner("در حال دریافت پاسخ منتور..."):
            try:
                # درخواست به API مدل
                API_URL = st.secrets.get("MODEL_ENDPOINT", "")
                API_KEY = st.secrets.get("HF_TOKEN", "")
                headers = {"Authorization": f"Bearer {API_KEY}"}
                payload = {"inputs": user_input}

                response = requests.post(API_URL, headers=headers, json=payload)
                result = response.json()

                # اگر مدل خروجی JSON داده باشد
                if isinstance(result, dict):
                    output_text = result.get("generated_text") or json.dumps(result)
                else:
                    output_text = result[0].get("generated_text", "")

                # تلاش برای پارس JSON خروجی
                try:
                    data = json.loads(output_text)
                    tone = data.get("tone", "academic")
                    msg = data.get("message", {})

                    st.markdown("<div class='mentor-box'>", unsafe_allow_html=True)
                    st.markdown(f"<div class='mentor-header'>🎓 منتور ({tone})</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='mentor-intro'>{msg.get('intro', '')}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='mentor-core'>{msg.get('core', '')}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='mentor-outro'>{msg.get('outro', '')}</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                except json.JSONDecodeError:
                    st.error("⚠️ فرمت پاسخ مدل معتبر نیست. لطفاً قالب JSON را در generator بررسی کنید.")
                    st.write(output_text)

            except Exception as e:
                st.error(f"خطایی رخ داد: {str(e)}")

#FEYZ
#DEO
