from datetime import datetime, timezone

from google.cloud.firestore import Query

from app.db import get_db

COL = "conversations"


def _col():
    return get_db().collection(COL)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create(title: str, messages: list[dict]) -> dict:
    payload = {"title": title, "messages": messages, "created_at": _now(), "updated_at": _now()}
    _, ref = _col().add(payload)
    return {"id": ref.id, **payload}


def list_all() -> list[dict]:
    """목록 응답에는 messages 를 넣지 않고 message_count 만 준다. 전체는 get()."""
    out = []
    for d in _col().order_by("updated_at", direction=Query.DESCENDING).stream():
        x = d.to_dict()
        out.append(
            {
                "id": d.id,
                "title": x.get("title", ""),
                "message_count": len(x.get("messages", [])),
                "updated_at": x.get("updated_at"),
            }
        )
    return out


def get(conv_id: str):
    d = _col().document(conv_id).get()
    return {"id": d.id, **d.to_dict()} if d.exists else None


def append(conv_id: str, messages: list[dict]) -> bool:
    ref = _col().document(conv_id)
    snap = ref.get()
    if not snap.exists:
        return False
    ref.update({"messages": snap.to_dict().get("messages", []) + messages, "updated_at": _now()})
    return True


def delete(conv_id: str) -> bool:
    ref = _col().document(conv_id)
    if not ref.get().exists:
        return False
    ref.delete()
    return True
