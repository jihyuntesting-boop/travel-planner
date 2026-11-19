#!/usr/bin/env python3
"""국내 여행지 추천 프로그램: Gemini(LLM) + Kakao Local(장소 검색)."""
import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv 없이도 환경변수만으로 동작
    pass

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
KAKAO_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
TIMEOUT = 30
REQUIRED_KEYS = {"recommended_city": str, "weather": str, "events": list, "reason": str}


class ApiError(Exception):
    def __init__(self, err_type, message):
        super().__init__(message)
        self.err_type = err_type


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"날짜 형식이 올바르지 않습니다: {value!r} (예: 2026-03-15)")


def http_error(status):
    if status in (401, 403):
        return "AUTH_ERROR"
    if status == 429:
        return "QUOTA_ERROR"
    return "HTTP_ERROR"


def call_gemini(prompt, json_mode=False):
    """Gemini generateContent 호출(POST). 응답 텍스트를 반환한다."""
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    if json_mode:
        body["generationConfig"] = {"responseMimeType": "application/json"}
    try:
        r = requests.post(
            GEMINI_URL.format(model=model),
            headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"},
            json=body, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise ApiError("NETWORK_ERROR", type(e).__name__)
    if r.status_code != 200:
        raise ApiError(http_error(r.status_code), f"HTTP {r.status_code}")
    try:
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, ValueError):
        raise ApiError("PARSE_ERROR", "Gemini 응답 구조가 예상과 다릅니다")


def extract_json(text):
    """코드펜스가 섞여 있어도 JSON 객체를 추출한다."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text)


def validate_plan(data):
    if not isinstance(data, dict):
        raise ValueError("JSON 객체가 아닙니다")
    for k, t in REQUIRED_KEYS.items():
        if not isinstance(data.get(k), t):
            raise ValueError(f"필수 키 누락 또는 타입 오류: {k}")
    return data


def recommend(date, errors):
    prompt = (
        f"여행 날짜 {date} 에 국내에서 여행하기 좋은 지역 1곳을 추천하세요. "
        "반드시 아래 키만 가진 JSON 객체 하나만 출력하세요(설명 문장 금지).\n"
        '{"recommended_city": "도시명(string)", "weather": "해당 시기 일반적 날씨 요약(string)", '
        '"events": ["행사/축제 후보 1~3개(string)"], "reason": "추천 근거 2~4문장(string)"}')
    last = None
    for attempt in range(2):  # 최초 1회 + 재시도 1회
        text = call_gemini(prompt, json_mode=True)
        try:
            return validate_plan(extract_json(text))
        except (ValueError, json.JSONDecodeError) as e:
            last = e
            errors.append({"step": "llm_recommend", "type": "PARSE_ERROR",
                           "message": f"attempt {attempt + 1}: {e}"})
            prompt = ("앞선 출력은 JSON 파싱에 실패했습니다. 키 recommended_city, weather, events(배열), reason 만 "
                      f"포함한 JSON 객체 하나만 다시 출력하세요. 여행 날짜: {date}")
    raise ApiError("PARSE_ERROR", f"추천 JSON 파싱 실패: {last}")


def search_places(city, errors, size=5):
    """Kakao Local 키워드 검색(GET). 실패해도 빈 리스트를 반환한다."""
    query = f"{city} 맛집"
    try:
        r = requests.get(
            KAKAO_URL,
            headers={"Authorization": f"KakaoAK {os.environ['KAKAO_REST_API_KEY']}"},
            params={"query": query, "category_group_code": "FD6", "size": size},
            timeout=TIMEOUT)
        if r.status_code != 200:
            raise ApiError(http_error(r.status_code), f"HTTP {r.status_code}")
        docs = r.json().get("documents", [])
    except requests.RequestException as e:
        errors.append({"step": "place_search", "type": "NETWORK_ERROR", "message": type(e).__name__})
        return []
    except ApiError as e:
        errors.append({"step": "place_search", "type": e.err_type, "message": str(e)})
        return []
    except ValueError:
        errors.append({"step": "place_search", "type": "PARSE_ERROR", "message": "응답 JSON 파싱 실패"})
        return []
    places = []
    for d in docs:
        places.append({
            "name": d.get("place_name", ""),
            "address": d.get("road_address_name") or d.get("address_name", ""),
            "category": d.get("category_name", ""),
            "url": d.get("place_url", ""),
            "x": float(d["x"]) if d.get("x") else None,
            "y": float(d["y"]) if d.get("y") else None,
        })
    if not places:
        errors.append({"step": "place_search", "type": "EMPTY_RESULT", "message": f"0 results for query={query}"})
    return places


def fallback_report(date, plan, places, errors):
    """LLM 리포트 생성에 실패했을 때 쓰는 최소 리포트."""
    events = "\n".join(f"- {e}" for e in plan["events"]) or "- 데이터 없음"
    return (f"## 추천 지역\n{plan['recommended_city']}\n\n## 추천 이유\n{plan['reason']}\n\n"
            f"## 날씨 요약\n{plan['weather']}\n\n## 행사/축제\n{events}\n\n"
            "## 1일 일정 제안\n- 데이터 없음 (리포트 생성 LLM 호출 실패)\n")


def build_report(date, plan, places, errors):
    prompt = (
        "아래 데이터로 국내 여행 리포트를 한국어 Markdown 으로 작성하세요. 제목(# )은 쓰지 말고, "
        "정확히 다음 순서의 '## ' 섹션만 출력하세요: 추천 지역, 추천 이유, 날씨 요약, 행사/축제, 맛집 추천, "
        "1일 일정 제안(오전/오후/저녁). 맛집 목록이 비어 있으면 맛집 추천 섹션에 '- 데이터 없음'만 쓰세요. "
        "목록에 없는 맛집은 지어내지 마세요.\n\n"
        f"여행 날짜: {date}\n추천 JSON: {json.dumps(plan, ensure_ascii=False)}\n"
        f"맛집 목록: {json.dumps(places, ensure_ascii=False)}")
    try:
        body = call_gemini(prompt).strip()
    except ApiError as e:
        errors.append({"step": "llm_report", "type": e.err_type, "message": str(e)})
        body = fallback_report(date, plan, places, errors)
    if not places and "데이터 없음" not in body:
        body += "\n\n## 맛집 추천\n- 데이터 없음 (장소 검색 결과 0건)\n"
    return body


def errors_section(errors):
    if not errors:
        return "## 오류 요약(errors)\n- 없음\n"
    lines = [f"- [{e['step']}] {e['type']}: {e['message']}" for e in errors]
    return "## 오류 요약(errors)\n" + "\n".join(lines) + "\n"


def check_keys():
    missing = [k for k in ("GEMINI_API_KEY", "KAKAO_REST_API_KEY") if not os.environ.get(k)]
    if missing:
        print(f"오류: 환경변수가 설정되지 않았습니다: {', '.join(missing)}")
        print("설정 방법: .env.example 을 .env 로 복사해 값을 채우거나, 터미널에서 export 하세요.")
        print('  예) export GEMINI_API_KEY="YOUR_KEY"   (Windows PowerShell: $env:GEMINI_API_KEY="YOUR_KEY")')
        sys.exit(1)


def main(argv=None):
    ap = argparse.ArgumentParser(description="날짜 기반 국내 여행지 추천 (Gemini + Kakao Local)")
    ap.add_argument("-date", "--date", required=True, type=parse_date, help='여행 날짜 "YYYY-MM-DD"')
    args = ap.parse_args(argv)
    date = args.date
    check_keys()
    errors = []
    out = Path("results")
    out.mkdir(exist_ok=True)

    print("[1/3] 1차 추천 생성 중(LLM)...")
    try:
        plan = recommend(date, errors)
    except ApiError as e:
        print(f"  - 오류: {e.err_type} ({e}). 종료합니다.")
        sys.exit(1)
    print(f"  - recommended_city: {plan['recommended_city']!r}")

    print("[2/3] 맛집 검색 중(지도/장소 API)...")
    places = search_places(plan["recommended_city"], errors)
    if places:
        print(f"  - 맛집 {len(places)}곳 검색 완료")
    else:
        print("  - 맛집 데이터 없음. '데이터 없음'으로 처리하고 계속 진행합니다.")
        for e in errors:
            if e["step"] == "place_search":
                print(f"  - 사유: {e['type']} ({e['message']})")

    print("[3/3] 최종 리포트 생성 중(LLM)...")
    body = build_report(date, plan, places, errors)
    print("  - 리포트 생성 완료")

    raw_path = out / f"{date}_raw.json"
    md_path = out / f"{date}_travel_plan.md"
    raw_path.write_text(json.dumps(
        {"date": date, "recommendation": plan, "places": places, "errors": errors},
        ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(f"# {date} 국내 여행 추천 리포트\n\n{body}\n\n{errors_section(errors)}", encoding="utf-8")
    print(f"\n완료! {md_path} 와 {raw_path} 를 확인하세요.")


if __name__ == "__main__":
    main()
