# app/generator.py
from __future__ import annotations
from typing import List, Dict, Any, Tuple
import textwrap
import json

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

def _extract_text_from_resp_dict(resp_dict: Dict[str, Any]) -> str:
    """
    استخراج متن سازگار با HF Router (OpenAI-compatible) و حالت‌های مختلف providers.
    """
    if not isinstance(resp_dict, dict):
        return ""
    choices = resp_dict.get("choices") or []
    if not choices:
        return ""
    ch = choices[0]

    # 1) حالت رایج: ch["message"]["content"]
    msg = ch.get("message")
    if isinstance(msg, dict):
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for p in content:
                if isinstance(p, dict):
                    # HF معمولاً {"type":"text","text":"..."}
                    if isinstance(p.get("text"), str):
                        parts.append(p["text"])
                    elif isinstance(p.get("content"), str):
                        parts.append(p["content"])
                    elif isinstance(p.get("data"), str):
                        parts.append(p["data"])
                elif isinstance(p, str):
                    parts.append(p)
            return "".join(parts)

    # 2) برخی providers متن را مستقیم داخل choice["text"] می‌گذارند
    if isinstance(ch.get("text"), str):
        return ch["text"]

    # 3) هیچ‌کدام نبود
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

    # 3) به دیکشنری ساده تبدیل کن (پوشش SDKهای مختلف)
    resp_dict: Dict[str, Any]
    if hasattr(resp, "model_dump"):               # OpenAI SDK v1
        resp_dict = resp.model_dump()
    elif hasattr(resp, "to_dict"):                # برخی کلاینت‌ها
        resp_dict = resp.to_dict()
    elif hasattr(resp, "dict"):
        resp_dict = resp.dict()
    else:
        # تلاش آخر: json → dict
        try:
            if hasattr(resp, "model_dump_json"):
                resp_dict = json.loads(resp.model_dump_json())
            else:
                resp_dict = json.loads(getattr(resp, "json", lambda: "{}")())
        except Exception:
            # در بدترین حالت، سعی می‌کنیم __dict__ را بخوانیم
            resp_dict = getattr(resp, "__dict__", {}) or {}

    # 4) robust extract
    answer = _extract_text_from_resp_dict(resp_dict).strip()

    return {
        "answer": answer,
        "sources": sources,
        "retrieved": [
            {"score": float(h.score), "source": h.metadata.get("source"), "preview": h.text[:200]}
            for h in hits
        ],
        "model": model,
    }
