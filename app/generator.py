# app/generator.py
from __future__ import annotations
from typing import List, Dict, Any, Tuple
import textwrap, json
from .deps import get_retriever, get_openai_client, get_model_name

SYSTEM_PROMPT = """\
You are an expert Persian mentor assistant (RAG). Answer in Persian unless asked otherwise.
Use the provided CONTEXT to ground your answer. If context is insufficient, say so.
Cite sources as [S1], [S2], ... from the retrieved list. Be concise and practical.
"""

def _format_context(chunks: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    lines, sources = [], []
    for i, ch in enumerate(chunks, 1):
        t = ch["text"].strip().replace("\n", " ")
        src = ch["metadata"].get("source")
        lines.append(f"[S{i}] {t}")
        sources.append({"tag": f"S{i}", "source": src})
    return "\n".join(lines), sources

def _build_messages(user_query: str, ctx_text: str) -> List[Dict[str, str]]:
    prompt = textwrap.dedent(f"""\
    CONTEXT:
    {ctx_text}
    ---
    پرسش کاربر:
    {user_query}
    """)
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}]

def _to_dict(resp: Any) -> Dict[str, Any]:
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

def _extract_text(resp_dict: Dict[str, Any]) -> str:
    choices = (resp_dict or {}).get("choices") or []
    if not choices:
        return ""
    ch = choices[0]
    # message.content can be str OR list[{"type":"text","text":...}]
    msg = ch.get("message") if isinstance(ch, dict) else {}
    if isinstance(msg, dict):
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for p in content:
                if isinstance(p, dict):
                    for k in ("text", "content", "data"):
                        if isinstance(p.get(k), str):
                            parts.append(p[k])
                            break
                elif isinstance(p, str):
                    parts.append(p)
            return "".join(parts)
    # some providers: choice.text
    if isinstance(ch, dict) and isinstance(ch.get("text"), str):
        return ch["text"]
    return ""

def generate_answer(user_query: str, k: int = 5, temperature: float = 0.3) -> Dict[str, Any]:
    retriever = get_retriever()
    client = get_openai_client()
    model = get_model_name()

    hits = retriever.search(user_query, k=k)
    chunks = [{"text": h.text, "score": h.score, "metadata": h.metadata} for h in hits]
    ctx_text, sources = _format_context(chunks) if chunks else ("", [])

    messages = _build_messages(user_query, ctx_text)
    resp = client.chat.completions.create(model=model, messages=messages, temperature=temperature)

    resp_dict = _to_dict(resp)
    answer = _extract_text(resp_dict).strip()

    return {
        "answer": answer,
        "sources": sources,
        "retrieved": [
            {"score": float(h.score), "source": h.metadata.get("source"), "preview": h.text[:200]}
            for h in hits
        ],
        "model": model,
    }