# app/generator.py
from __future__ import annotations
from typing import List, Dict, Any, Tuple
import textwrap
import json

from .deps import get_retriever, get_openai_client, get_model_name

SYSTEM_PROMPT = """\
You are an expert Persian mentor assistant (RAG). Answer in Persian unless asked otherwise.
Use the provided CONTEXT to ground your answer. If context is insufficient, say so.
Cite sources as [S1], [S2], ... from the retrieved list. Be concise and practical.
"""

def _format_context(chunks: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    lines, sources = [], []
    for i, ch in enumerate(chunks, 1):
        text = ch["text"].strip().replace("\n", " ")
        src = ch["metadata"].get("source")
        lines.append(f"[S{i}] {text}")
        sources.append({"tag": f"S{i}", "source": src})
    return "\n".join(lines), sources

def _build_messages(user_query: str, ctx_text: str) -> List[Dict[str, str]]:
    context_block = f"CONTEXT:\n{ctx_text}\n---\n"
    prompt = textwrap.dedent(f"""{context_block}
    پرسش کاربر:
    {user_query}
    """)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

def _resp_to_dict(resp: Any) -> Dict[str, Any]:
    # تبدیل امن خروجی کلاینت به dict
    for attr in ("model_dump", "to_dict", "dict"):
        if hasattr(resp, attr):
            try:
                return getattr(resp, attr)()
            except Exception:
                pass
    try:
        if hasattr(resp, "model_dump_json"):
            return json.loads(resp.model_dump_json())
        if hasattr(resp, "json"):
            j = resp.json() if callable(resp.json) else resp.json
            return json.loads(j) if isinstance(j, str) else j
    except Exception:
        pass
    return getattr(resp, "__dict__", {}) or {}

def _extract_answer(resp_dict: Dict[str, Any]) -> str:
    """
    از روی دیکشنری استاندارد OpenAI/HF متن را استخراج می‌کند.
    پوشش می‌دهد:
      - choices[0].message.content = str
      - choices[0].message.content = list[{ "type":"text", "text": ... }]
      - choices[0].text = str   (برخی providerها)
    """
    choices = (resp_dict or {}).get("choices") or []
    if not choices:
        return ""
    ch = choices[0]

    # message.content
    msg = ch.get("message") if isinstance(ch, dict) else None
    if isinstance(msg, dict):
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for p in content:
                if isinstance(p, dict):
                    for key in ("text", "content", "data"):
                        val = p.get(key)
                        if isinstance(val, str):
                            parts.append(val)
                            break
                elif isinstance(p, str):
                    parts.append(p)
            return "".join(parts)

    # choice.text (fallback)
    if isinstance(ch, dict):
        t = ch.get("text")
        if isinstance(t, str):
            return t

    return ""

def generate_answer(user_query: str, k: int = 5, temperature: float = 0.3) -> Dict[str, Any]:
    retriever = get_retriever()
    client = get_openai_client()
    model = get_model_name()

    # 1) retrieve context
    hits = retriever.search(user_query, k=k)
    chunks = [{"text": h.text, "score": h.score, "metadata": h.metadata} for h in hits]
    ctx_text, sources = _format_context(chunks) if chunks else ("", [])

    # 2) call LLM
    messages = _build_messages(user_query, ctx_text)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )

    # 3) extract final text robustly (dict-only, بدون .text)
    answer = _extract_answer(_resp_to_dict(resp)).strip()

    return {
        "answer": answer,
        "sources": sources,
        "retrieved": [
            {"score": float(h.score), "source": h.metadata.get("source"), "preview": h.text[:200]}
            for h in hits
        ],
        "model": model,
    }
