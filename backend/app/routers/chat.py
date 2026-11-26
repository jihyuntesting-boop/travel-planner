from fastapi import APIRouter, HTTPException

from app.schemas import ChatIn
from app.services import chat_service

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
def chat(body: ChatIn):
    try:
        return chat_service.chat(body.message, body.conversation_id)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    except Exception:
        raise HTTPException(502, "AI 응답을 가져오지 못했습니다. 잠시 후 다시 시도하세요.")
