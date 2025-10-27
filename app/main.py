from fastapi import FastAPI
from app.router_chat import chat_router

app = FastAPI()

app.include_router(chat_router)
