# app/main.py
from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.router_chat import router as chat_router
from app.generator import healthcheck as gen_health

app = FastAPI(title="Amin Mentor API", version="0.1.0")

# CORS برای UI لوکال
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # در دیپلوی نهایی محدودش کن
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def healthz():
    return {"ok": True, "generator": gen_health()}

@app.get("/version")
def version():
    return {"version": "0.1.0"}

app.include_router(chat_router)
