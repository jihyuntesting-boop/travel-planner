"""샘플 데이터 120개(여행 하루 경비)를 API 로 입력한다.
사용: API_BASE_URL=http://localhost:8000 python scripts/seed.py
"""
import json
import os
import random
import urllib.request
from datetime import date, timedelta

BASE = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
random.seed(7)
start = date(2026, 1, 1)
memos = ["식비 위주", "숙소 포함", "교통비 많음", "쇼핑", "입장료", "카페·간식", ""]

for i in range(120):
    d = start + timedelta(days=i)
    base = 60000 + i * 400  # 완만한 상승 추세
    value = int(base * random.uniform(0.6, 1.5) * (1.3 if d.weekday() >= 5 else 1))
    body = json.dumps({"date": d.isoformat(), "value": value, "memo": random.choice(memos)}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/data", body, {"Content-Type": "application/json"}, method="POST"
    )
    urllib.request.urlopen(req, timeout=60).read()
print("120건 입력 완료")
