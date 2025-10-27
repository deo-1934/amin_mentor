import os
import streamlit as st
from pathlib import Path
from deps import get_retriever, get_openai_client
from generator import generate_response

st.set_page_config(page_title="Amin Mentor Demo", page_icon="🤖", layout="centered")

st.title("🤖 Amin Mentor — Demo")
st.caption("حالت Full با کلید OpenAI | حالت Demo (بدون کلید)")

msg = st.text_input("سؤال را بنویس:", value="این پروژه چطور کار می‌کند؟")

if st.button("اجرا"):
    # اطمینان از ایندکس دمو
    ROOT = Path(__file__).parent
    DATA = ROOT / "data"
    FAISS_DIR = ROOT / "faiss_index"
    DATA.mkdir(exist_ok=True)
    demo_file = DATA / "demo.txt"

    # بازیابی اطلاعات مرتبط با سوال
    retriever = get_retriever()
    retrieved_data = retriever.retrieve(msg)

    # تولید پاسخ با استفاده از مدل
    response = generate_response(msg, retrieved_data)

    # نمایش پاسخ
    st.write("پاسخ:")
    st.write(response)
