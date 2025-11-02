#FEYZ
#DEO
import os
from typing import Literal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_CHEAP = os.getenv("OPENAI_MODEL_CHEAP", "gpt-4o-mini")
MODEL_DEEP = os.getenv("OPENAI_MODEL_DEEP", "gpt-4o")

app = FastAPI(title="Amin Mentor API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "message": "Amin Mentor API is running successfully 🚀"}

class ChatRequest(BaseModel):
    message: str
    mode: Literal["cheap", "deep"] = "cheap"

@app.post("/chat")
async def chat(request: ChatRequest):
    if not OPENAI_API_KEY:
        return {"error": "Missing OPENAI_API_KEY in Render Environment"}
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    model_name = MODEL_DEEP if request.mode == "deep" else MODEL_CHEAP

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": request.message}],
        )
        answer = completion.choices[0].message.content
        return {"response": answer}
    except Exception as e:
        return {"error": str(e)}

#DEO
