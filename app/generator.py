# app/generator.py
from __future__ import annotations
from typing import List, Dict, Any, Tuple
import textwrap
import os

from .deps import get_retriever, get_openai_client, get_model_name

SYSTEM_PROMPT = """\
You are an expert Persian mentor assistant (RAG). Answer in Persian unless the user asks otherwise.
- Use the provided CONTEXT to ground your answer.
- If context is insufficient, say so briefly and ask for more details.
- Cite retrieved sources inline as [S1], [S2], ... based on the list of sources you get.
- Be concise, clear, and practical.
"""

def _format_context(chunks: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    lines = []
    sources: List[Dict[str, Any]] = []
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

def generate_answer(user_query: str, k: int = 5, temperature: float = 0.3) -> Dict[str, Any]:
    retriever = get_retriever()
    client = get_openai_client()
    model = get_model_name()

    # 1) retrieve context
    hits = retriever.search(user_query, k=k)
    chunks = [
        {"text": h.text, "score": h.score, "metadata": h.metadata}
        for h in hits
    ]
    ctx_text, sources = _format_context(chunks) if chunks else ("", [])

    # 2) build messages
    messages = _build_messages(user_query, ctx_text)

    # 3) call Hugging Face (OpenAI-compatible)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )

    # 4) extract text safely across providers
    raw_choice = resp.choices[0]
    msg = getattr(raw_choice, "message", None) or {}

    if isinstance(msg, dict):
        content = msg.get("content")
        if isinstance(content, str):
            answer = content
        elif isinstance(content, list):
            parts = []
            for p in content:
                if isinstance(p, dict):
                    if "text" in p and isinstance(p["text"], str):
                        parts.append(p["text"])
                    elif "content" in p and isinstance(p["content"], str):
                        parts.append(p["content"])
                    elif "data" in p and isinstance(p["data"], str):
                        parts.append(p["data"])
                elif isinstance(p, str):
                    parts.append(p)
            answer = "".join(parts)
        else:
            answer = getattr(raw_choice, "text", "") or ""
    else:
        content = getattr(msg, "content", None)
        if isinstance(content, str):
            answer = content
        elif isinstance(content, list):
            answer = "".join(
                (getattr(part, "text", None) or getattr(part, "content", "") or str(part))
                for part in content
            )
        else:
            answer = getattr(raw_choice, "text", "") or ""

    answer = str(answer).strip()

    return {
        "answer": answer,
        "sources": sources,
        "retrieved": [
            {
                "score": float(h.score),
                "source": h.metadata.get("source"),
                "preview": h.text[:200]
            } for h in hits
        ],
        "model": model,
    }
