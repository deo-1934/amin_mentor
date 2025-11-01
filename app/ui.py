#FEYZ
#DEO
# app/ui.py
# -*- coding: utf-8 -*-
"""
Amin Mentor — End-User UI (Presentation Mode, no source-count control)
- طراحی شیک و مینیمال برای کاربر نهایی
- بدون نمایش جزئیات فنی/دیباگ
- بدون کنترل «تعداد منابع» (به‌صورت داخلی روی 4)
- پاسخ آفلاین: هیچ API خارجی لازم نیست
"""

from __future__ import annotations
import io
import time
from datetime import datetime
from typing import Any, Dict, List

import streamlit as st

# --- Import project modules (both package/script modes) ---
try:
    from . import retriever, generator  # type: ignore
except Exception:  # pragma: no cover
    import retriever  # type: ignore
    import generator  # type: ignore

# ---------------------- Page Config ----------------------
st.set_page_config(
    page_title="Amin Mentor",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------- Style ---------------------------
_CUSTOM_CSS = """
<style>
.block-container { padding-top: 1.25rem !important; }
.hero {
  padding: 1.2rem 1.4rem;
  border-radius: 18px;
  border: 1px solid rgba(120,120,120,0.18);
  background: linear-gradient(180deg, rgba(255,255,255,0.7), rgba(255,255,255,0.5));
}
[data-theme="dark"] .hero {
  background: radial-gradient(80% 80% at 50% 0%, rgba(30,30,30,0.7), rgba(30,30,30,0.5));
  border-color: rgba(255,255,255,0.1);
}
.bubble {
  border: 1px solid rgba(120,120,120,0.2);
  border-radius: 16px;
  padding: 0.9rem 1rem;
  line-height: 1.7;
  margin: .35rem 0;
}
.user { background: rgba(120, 180, 255, 0.14); }
.bot  { background: rgba(140, 255, 200, 0.12); }
.source {
  border-left: 3px solid rgba(120,120,120,0.35);
  padding: .5rem .75rem;
  border-radius: 6px;
  font-size: .94rem;
  margin: .35rem 0;
  background: rgba(0,0,0,0.02);
}
[data-theme="dark"] .source { background: rgba(255,255,255,0.02); }
.footer-note { opacity: .75; font-size: .85rem; }
</style>
"""
st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------- State ---------------------------
def _init_state():
    if "chat" not in st.session_state:
        st.session_state.chat = []  # list[dict]: {"role": "user"/"assistant", "text": str, "sources": list[dict]}
    if "last_answer" not in st.session_state:
        st.session_state.last_answer = ""

_init_state()

# ---------------------- Helpers -------------------------
def _snip(text: str, n: int = 280) -> str:
    text = (text or "").strip()
    return (text[: n - 1] + "…") if len(text) > n else text

def _source_title(meta: Dict[str, Any]) -> str:
    for k in ("title", "source", "file", "filename", "path", "name", "doc_id", "id"):
        if meta and meta.get(k):
            return str(meta[k])
    return "منبع"

@st.cache_data(show_spinner=False)
def _retrieve(query: str, k: int = 4) -> List[Dict[str, Any]]:
    # tolerant to slight signature differences
    items = []
    if hasattr(retriever, "retrieve"):
        try:
            out = retriever.retrieve(query, k=k)  # type: ignore
        except TypeError:
            out = retriever.retrieve(query)  # type: ignore
        if isinstance(out, list):
            items = out[:k]
    # normalize
    norm = []
    for it in items:
        if isinstance(it, dict):
            text = it.get("text") or it.get("chunk") or it.get("content") or ""
            meta = it.get("meta") or it.get("metadata") or {}
            score = it.get("score")
        elif isinstance(it, (list, tuple)) and it:
            text, score, meta = str(it[0]), (it[1] if len(it) > 1 else None), {}
        else:
            text, score, meta = str(it), None, {}
        norm.append({"text": text, "score": score, "meta": meta})
    return norm

def _generate(question: str, context_texts: List[str], max_new_tokens: int = 256) -> str:
    # Prefer offline generate_answer if available
    if hasattr(generator, "generate_answer"):
        return generator.generate_answer(question, context_texts, max_new_tokens=max_new_tokens)  # type: ignore
    if hasattr(generator, "generate_hybrid_answer"):
        return generator.generate_hybrid_answer(question, context_texts, max_new_tokens=max_new_tokens)  # type: ignore
    # offline minimal fallback (no API)
    joined = "\n\n".join(context_texts[:3]) if context_texts else "—"
    return (
        f"سؤال: {question}\n\n"
        f"خلاصه منابع:\n{joined}\n\n"
        f"جمع‌بندی: پاسخ آفلاین با تکیه بر بخش‌های مرتبط ارائه شد."
    )

def _export_markdown() -> bytes:
    lines = [f"# Amin Mentor — Transcript ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n"]
    for turn in st.session_state.chat:
        role = "کاربر" if turn["role"] == "user" else "دستیار"
        lines.append(f"**{role}:**\n\n{turn['text']}\n")
        if turn["role"] == "assistant" and turn.get("sources"):
            lines.append("\n**منابع:**\n")
            for i, s in enumerate(turn["sources"], 1):
                title = _source_title(s.get("meta") or {})
                preview = _snip(s.get("text", ""), 180)
                lines.append(f"{i}. {title}: {preview}")
            lines.append("")
        lines.append("---\n")
    return ("\n".join(lines)).encode("utf-8")

#FEYZ
#DEO

# ---------------------- Hero ----------------------------
col1, col2 = st.columns([0.75, 0.25])
with col1:
    st.markdown(
        "<div class='hero'>"
        "<h1 style='margin:0;'>🧠 Amin Mentor</h1>"
        "<div style='opacity:.85;margin-top:.25rem;'>پرسش خود را بپرسید؛ من خلاصه‌ای دقیق و قابل اعتماد از منابع داخلی ارائه می‌دهم.</div>"
        "</div>",
        unsafe_allow_html=True,
    )
with col2:
    st.write("")
    st.write("")
    st.markdown(
        f"<div style='text-align:center' class='hero'>"
        f"<div>وضعیت سرویس</div>"
        f"<div style='margin-top:.35rem'>آفلاینِ امن · بدون API خارجی</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------- Controls (no source-count UI) ---
question = st.text_input(
    "سؤال شما",
    placeholder="مثلاً: «منتور شخصی امین چه کاری انجام می‌دهد؟»",
)
show_sources = st.checkbox("نمایش منابع", value=True)

run_col, clear_col, export_col = st.columns([0.25, 0.25, 0.5])
with run_col:
    ask = st.button("ارسال سؤال", type="primary", use_container_width=True)
with clear_col:
    if st.button("پاک کردن گفتگو", use_container_width=True):
        st.session_state.chat = []
        st.session_state.last_answer = ""
        st.success("گفتگو پاک شد.")
with export_col:
    md = _export_markdown()
    st.download_button(
        label="دانلود متن گفتگو (Markdown)",
        data=md,
        file_name=f"amin-mentor-transcript-{datetime.now().strftime('%Y%m%d-%H%M')}.md",
        mime="text/markdown",
        use_container_width=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------- Pipeline ------------------------
if ask:
    if not question or not question.strip():
        st.warning("لطفاً ابتدا سؤال را وارد کنید.")
    else:
        q = question.strip()
        st.session_state.chat.append({"role": "user", "text": q, "sources": []})

        with st.spinner("در حال جست‌وجوی منابع مرتبط…"):
            t0 = time.time()
            retrieved = _retrieve(q, k=4)  # ثابت: 4 منبع
            _ = time.time() - t0

        sources_for_turn = retrieved if show_sources else []

        with st.spinner("در حال تولید پاسخ…"):
            ctx = [x.get("text", "") for x in retrieved]
            answer = _generate(q, ctx, max_new_tokens=256)

        st.session_state.last_answer = answer
        st.session_state.chat.append(
            {"role": "assistant", "text": answer, "sources": sources_for_turn}
        )

# ---------------------- Render Chat ---------------------
if st.session_state.chat:
    for turn in st.session_state.chat:
        role = turn["role"]
        css = "user" if role == "user" else "bot"
        icon = "👤" if role == "user" else "🤖"
        st.markdown(
            f"<div class='bubble {css}'>{icon} {turn['text']}</div>",
            unsafe_allow_html=True,
        )
        if role == "assistant" and show_sources and turn.get("sources"):
            with st.expander("منابع استفاده‌شده", expanded=False):
                for i, s in enumerate(turn["sources"], 1):
                    meta = s.get("meta") or {}
                    title = _source_title(meta)
                    snippet = _snip(s.get("text", ""))
                    
                    st.markdown(
                        f"<div class='source'><b>{i}. {title}</b><br>{snippet}</div>",
                        unsafe_allow_html=True,
                    )

# ---------------------- Footer --------------------------
st.divider()
st.caption(
    "© Amin Mentor — نسخهٔ ارائه برای کاربر. پاسخ‌ها بر مبنای منابع داخلی جمع‌آوری و خلاصه‌سازی می‌شوند."
)
