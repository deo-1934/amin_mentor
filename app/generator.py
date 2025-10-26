# app/generator.py
from __future__ import annotations
from typing import List, Dict, Any, Tuple
import textwrap

from .deps import get_retriever, get_openai_client, get_model_name

SYSTEM_PROMPT = """\
You are an expert Persian mentor assistant (RAG). Answer in Persian unless the user asks otherwise.
- Use the provided CONTEXT to ground your answer.
- If context is insufficient, say so briefly and ask for more details.
- Cite retrieved sources inline as [S1], [S2], ... based on the list of sources you get.
- Be concise, clear, and practical.
"""

def _format_context(chunks: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    lines, sources = [], []
    for i, ch in enumerate(chunks, 1):
        src = ch["metadata"].get("source")
        text = ch["text"].strip().replace("\n", " ")
        lines.append(f"[S{i}] {text}")
        sources.append({"tag": f"S{i}", "source": src})
    return "\n".join(lines), sources

def _build_messages(user_query: str, ctx_text: str) -> List[Dict[str, str]]:
    context_block = f"CONTEXT:\n{ctx_text}\n---\n"
    prompt = textwrap.dedent(f"""\
    {context_block}
    پرسش کاربر:
    {user_query}

    راهنما:
    - از محتوای CONTEXT استفاده کن و هر جا لازم بود ارجاع [S#] بده.
    - اگر چیزی در کانتکست نبود، شفاف بگو و حدس نزن.
    """)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

def _extract_text_from_choice(choice: Any) -> str:
    """
    سازگار با چندین فرمت پاسخ:
    - OpenAI SDK: choice.message.content (str|list[parts])
    - HF Router (openai-compatible): choice.message.content -> list of dicts [{'type':'text','text':...}, ...]
    - برخی ارائه‌دهنده‌ها: choice.text
    - یا حتی ساختارهای دیکشنری
    """
    # اگر آبجکت شبیه dict بود:
    if isinstance(choice, dict):
        msg = choice.get("message") or {}
        # گاهی متن مستقیم در choice["text"] است
        if "text" in choice and isinstance(choice["text"], str):
            return choice["text"]
        # پیام
        if isinstance(msg, dict):
            content = msg.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts: List[str] = []
                for p in content:
                    if isinstance(p, dict):
                        # حالت‌های متداول HF
                        if isinstance(p.get("text"), str):
                            parts.append(p["text"])
                        elif isinstance(p.get("content"), str):
                            parts.append(p["content"])
                        elif isinstance(p.get("data"), str):
                            parts.append(p["data"])
                    elif isinstance(p, str):
                        parts.append(p)
                return "".join(parts)
        return ""
    # آبجکت typed (OpenAI SDK)
    msg = getattr(choice, "message", None)
    # اگر خود choice متن داشت
    direct_text = getattr(choice, "text", None)
    if isinstance(direct_text, str) and direct_text.strip():
        return direct_text
    # پیام دارای content
    if msg is not None:
        content = getattr(msg, "content", None)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            pieces: List[str] = []
            for part in content:
                # part ممکن است dict یا typed باشد
                if isinstance(part, dict):
                    if isinstance(part.get("text"), str):
                        pieces.append(part["text"])
                    elif isinstance(part.get("content"), str):
                        pieces.append(part["content"])
                    elif isinstance(part.get("data"), str):
                        pieces.append(part["data"])
                else:
                    t = getattr(part, "text", None)
                    if isinstance(t, str):
                        pieces.append(t)
                    else:
                        c = getattr(part, "content", None)
                        if isinstance(c, str):
                            pieces.append(c)
                        else:
                            pieces.append(str(part))
            return "".join(pieces)
    return ""

def generate_answer(user_query: str, k: int = 5, temperature: float = 0.3) -> Dict[str, Any]:
    retriever = get_retriever()
    client = get_openai_client()
    model = get_model_name()

    # 1) retrieve context
    hits = retriever.search(user_query, k=k)
    chunks = [{"text": h.text, "score": h.score, "metadata": h.metadata} for h in hits]
    ctx_text, sources = _format_context(chunks) if chunks else ("", [])

    # 2) LLM call
    messages = _build_messages(user_query, ctx_text)
    resp = client.chat.completions.create(model=model, messages=messages, temperature=temperature)

    # 3) robust text extraction
    choice0 = resp.choices[0]
    answer = _extract_text_from_choice(choice0).strip()

    return {
        "answer": answer,
        "sources": sources,
        "retrieved": [
            {"score": float(h.score), "source": h.metadata.get("source"), "preview": h.text[:200]}
            for h in hits
        ],
        "model": model,
    }
