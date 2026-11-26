from app.db import get_db

COL = "data"


def _col():
    return get_db().collection(COL)


def _payload(item: dict) -> dict:
    return {"date": item["date"].isoformat(), "value": item["value"], "memo": item["memo"]}


def create(item: dict) -> dict:
    payload = _payload(item)
    _, ref = _col().add(payload)
    return {"id": ref.id, **payload}


def list_all() -> list[dict]:
    out = []
    for d in _col().order_by("date").stream():
        x = d.to_dict()
        out.append({"id": d.id, "date": x["date"], "value": x["value"], "memo": x.get("memo", "")})
    return out


def update(doc_id: str, item: dict):
    ref = _col().document(doc_id)
    if not ref.get().exists:
        return None
    payload = _payload(item)
    ref.set(payload)
    return {"id": doc_id, **payload}


def delete(doc_id: str) -> bool:
    ref = _col().document(doc_id)
    if not ref.get().exists:
        return False
    ref.delete()
    return True
