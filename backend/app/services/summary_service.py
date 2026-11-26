import statistics
from collections import defaultdict
from datetime import date

from app.services import data_service

TREND_WINDOW = 30  # 최근 30일 vs 직전 30일


def _trend(rows: list[dict]) -> str:
    if len(rows) < 2:
        return "데이터 부족"
    last = date.fromisoformat(rows[-1]["date"])
    recent, prev = [], []
    for r in rows:
        age = (last - date.fromisoformat(r["date"])).days
        if age < TREND_WINDOW:
            recent.append(r["value"])
        elif age < TREND_WINDOW * 2:
            prev.append(r["value"])
    if not recent or not prev:
        return "데이터 부족"
    ra, pa = sum(recent) / len(recent), sum(prev) / len(prev)
    if pa == 0:
        return "데이터 부족"
    pct = (ra - pa) / pa * 100
    label = "상승" if pct > 5 else "하락" if pct < -5 else "유지"
    return f"{label} (최근 {TREND_WINDOW}일 평균이 직전 {TREND_WINDOW}일 대비 {pct:+.1f}%)"


def build_summary(rows: list[dict] | None = None) -> dict:
    rows = data_service.list_all() if rows is None else rows
    if not rows:
        return {"period": None, "count": 0, "metrics": {}, "trend": "데이터 없음"}
    values = [r["value"] for r in rows]
    best = max(rows, key=lambda r: r["value"])
    worst = min(rows, key=lambda r: r["value"])
    return {
        "period": f'{rows[0]["date"]} ~ {rows[-1]["date"]}',
        "count": len(rows),
        "metrics": {
            "total": round(sum(values)),
            "average": round(sum(values) / len(values)),
            "median": round(statistics.median(values)),
            "stdev": round(statistics.pstdev(values)),  # 추가 지표(보너스)
            "max": round(best["value"]),
            "max_date": best["date"],
            "min": round(worst["value"]),
            "min_date": worst["date"],
        },
        "trend": _trend(rows),
    }


def build_statistics() -> dict:
    """차트용 시계열 + 월별 집계 (보너스)."""
    rows = data_service.list_all()
    monthly = defaultdict(list)
    for r in rows:
        monthly[r["date"][:7]].append(r["value"])
    return {
        "series": [{"date": r["date"], "value": r["value"]} for r in rows],
        "monthly": [
            {"month": m, "total": round(sum(v)), "average": round(sum(v) / len(v)), "count": len(v)}
            for m, v in sorted(monthly.items())
        ],
    }
