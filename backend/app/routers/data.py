from fastapi import APIRouter, HTTPException

from app.schemas import DataIn, DataOut
from app.services import data_service, summary_service

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("", response_model=DataOut, status_code=201)
def create_data(body: DataIn):
    return data_service.create(body.model_dump())


@router.get("", response_model=list[DataOut])
def list_data():
    return data_service.list_all()


@router.get("/summary")
def get_summary():
    """프롬프트 주입용 요약."""
    return summary_service.build_summary()


@router.get("/statistics")
def get_statistics():
    """차트·월별 통계 (보너스)."""
    return summary_service.build_statistics()


@router.put("/{data_id}", response_model=DataOut)
def update_data(data_id: str, body: DataIn):
    out = data_service.update(data_id, body.model_dump())
    if out is None:
        raise HTTPException(404, "데이터를 찾을 수 없습니다.")
    return out


@router.delete("/{data_id}")
def delete_data(data_id: str):
    if not data_service.delete(data_id):
        raise HTTPException(404, "데이터를 찾을 수 없습니다.")
    return {"deleted": data_id}
