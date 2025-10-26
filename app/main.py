# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .router_chat import router as chat_router

app = FastAPI(title="Amin Mentor - Personal Mentor (RAG)")

# CORS (در صورت نیاز)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)

@app.get("/")
def root():
    return {"ok": True, "app": "Amin Mentor - RAG Chat"}
