# app/router_chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

from .generator import generate_answer

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    message: str = Field(..., description="User question in Persian or English")
    k: int = Field(5, ge=1, le=10, description="top-k retrieval")
    temperature: float = Field(0.3, ge=0.0, le=1.0)

class SourceOut(BaseModel):
    tag: str
    source: Optional[str] = None

class RetrievedOut(BaseModel):
    score: float
    source: Optional[str]
    preview: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceOut] = []
    retrieved: List[RetrievedOut] = []
    model: str

@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        out = generate_answer(req.message, k=req.k, temperature=req.temperature)
        return ChatResponse(**out)
    except FileNotFoundError as e:
        # ایندکس پیدا نشد
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"chat_error: {e}")
