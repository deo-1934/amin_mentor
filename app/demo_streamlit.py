import os
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Amin Mentor Demo", page_icon="🤖", layout="centered")

st.title("🤖 Amin Mentor — Demo")
st.caption("حالت Full با کلید OpenAI | حالت Demo بدون کلید (ماک)")

msg = st.text_input("سؤال را بنویس:", value="این پروژه چطور کار می‌کند؟")
k = st.slider("Top-K", 1, 10, 5)
temp = st.slider("Temperature", 0.0, 1.0, 0.3)

if st.button("اجرا"):
    # اطمینان از ایندکس دمو
    ROOT = Path(__file__).parent
    DATA = ROOT / "data"
    FAISS_DIR = ROOT / "faiss_index"
    DATA.mkdir(exist_ok=True)
    demo_file = DATA / "demo.txt"
    if not demo_file.exists() or demo_file.stat().st_size == 0:
        demo_file.write_text("این یک سند تستی برای دمو است.", encoding="utf-8")
    if not FAISS_DIR.exists() or not any(FAISS_DIR.iterdir()):
        import subprocess, sys
        st.info("⏳ در حال ساخت ایندکس...")
        code = subprocess.call([sys.executable, str(ROOT / "ingest" / "build_faiss.py")])
        if code != 0:
            st.error("⛔️ خطا در ساخت ایندکس.")
            st.stop()

    has_key = bool(os.environ.get("OPENAI_API_KEY"))
    if has_key:
        try:
            from app.generator import generate_answer
            resp = generate_answer(message=msg, k=k, temperature=temp)
            st.success("Full Mode (با مدل)")
            st.markdown(resp.answer)
            if resp.sources:
                st.subheader("منابع")
                for s in resp.sources:
                    st.write(f"- {s.title or s.url or s.chunk_id}")
        except Exception as e:
            st.warning(f"Full Mode شکست خورد: {e}")
    else:
        from app import deps
        retriever = deps.get_retriever()
        results = retriever.search(msg, k=k)
        st.info("Demo Mode (بدون کلید) — نمایش کانتکست بازیابی‌شده")
        for i, r in enumerate(results, 1):
            st.write(f"**[{i}]**")
            txt = (r.text or "").strip()
            if len(txt) > 600:
                txt = txt[:600] + "…"
            st.code(txt)
