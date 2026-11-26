from datetime import date as Date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class DataIn(BaseModel):
    date: Date
    value: float = Field(..., ge=0, le=1e12, description="값(예: 하루 여행 경비, 원)")
    memo: str = Field("", max_length=200)


class DataOut(DataIn):
    id: str


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class ConversationIn(BaseModel):
    title: str = Field("새 대화", max_length=100)
    messages: list[Message] = Field(..., min_length=1, max_length=200)


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    conversation_id: Optional[str] = None
