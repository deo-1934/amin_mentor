from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.generator import generate_answer  # دقت کن: app.generator

chat_router = APIRouter()

@chat_router.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        message = data.get("message", "")
        response_text = generate_answer(message)
        return JSONResponse(content={"response": response_text})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"chat_error: {e}"}
        )
