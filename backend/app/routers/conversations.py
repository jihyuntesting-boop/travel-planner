from fastapi import APIRouter, HTTPException

from app.schemas import ConversationIn
from app.services import conversation_service

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", status_code=201)
def save_conversation(body: ConversationIn):
    return conversation_service.create(body.title, [m.model_dump() for m in body.messages])


@router.get("")
def list_conversations():
    """목록 응답에는 messages 를 포함하지 않는다(message_count 만). 전체는 GET /{id}."""
    return conversation_service.list_all()


@router.get("/{conv_id}")
def get_conversation(conv_id: str):
    conv = conversation_service.get(conv_id)
    if conv is None:
        raise HTTPException(404, "대화를 찾을 수 없습니다.")
    return conv


@router.delete("/{conv_id}")
def delete_conversation(conv_id: str):
    if not conversation_service.delete(conv_id):
        raise HTTPException(404, "대화를 찾을 수 없습니다.")
    return {"deleted": conv_id}
