# app/router_chat.py
from __future__ import annotations
import time
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.retriever import retrieve
from app.generator import generate_answer

router = APIRouter(prefix="", tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    top_k: int = 5
    max_new_tokens: int = 200

class Snippet(BaseModel):
    text: str
    source: dict | None = None
    distance: float | None = None

class ChatResponse(BaseModel):
    answer: str
    context: List[Snippet]
    took_ms: int

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    t0 = time.time()
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")

    # 1) Retrieve
    hits = retrieve(req.message, top_k=req.top_k)
    ctx_texts = [h["text"] for h in hits if h.get("text")]

    # 2) Generate
    answer = generate_answer(req.message, context=ctx_texts, max_new_tokens=req.max_new_tokens)

    took = int((time.time() - t0) * 1000)
    return ChatResponse(
        answer=answer,
        context=[Snippet(**h) for h in hits],
        took_ms=took,
    )
