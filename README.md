# 국내 여행지 추천 프로그램

여행 날짜를 입력하면 **Gemini(LLM)** 가 시기에 맞는 지역·날씨·행사를 JSON으로 추천하고,
**Kakao Local API** 로 그 지역 맛집을 검색한 뒤, 다시 Gemini 로 최종 Markdown 리포트를 만듭니다.

흐름: 날짜 → [LLM] 추천 JSON → [Kakao] 맛집 검색 → [LLM] 리포트 → `results/` 저장

## 실행 방법
Python 3.10 이상이 필요합니다.

```bash
pip install -r requirements.txt
cp .env.example .env   # 열어서 키 입력
python travel_planner.py --date "2026-03-15"
```

`-date` 와 `--date` 둘 다 사용할 수 있습니다. 날짜 형식이 틀리면 사용법을 출력하고 종료합니다.

## API 키 설정
- Gemini: Google AI Studio 에서 발급 → `GEMINI_API_KEY`
- Kakao: Kakao Developers 에서 앱 생성 후 REST API 키 → `KAKAO_REST_API_KEY`
  (카카오 로컬 API 사용 설정이 켜져 있어야 합니다. 401/403 이면 키·권한을 점검하세요.)

`.env` 대신 환경변수도 가능합니다.
```bash
export GEMINI_API_KEY="YOUR_KEY"
export KAKAO_REST_API_KEY="YOUR_KEY"
```
Windows PowerShell: `$env:GEMINI_API_KEY="YOUR_KEY"`

키가 없으면 프로그램은 설정 방법을 안내하고 즉시 종료합니다.

## 결과물 확인
- `results/<날짜>_travel_plan.md`: 최종 리포트
- `results/<날짜>_raw.json`: 1차 추천 JSON, 맛집 목록, `errors`

## 오류 처리
- 장소 검색 실패/0건: 맛집을 "데이터 없음"으로 처리하고 계속 진행, `errors` 에 기록
- LLM JSON 파싱 실패: 1회만 재요청, 그래도 실패하면 종료
- 리포트 LLM 호출 실패: 최소 리포트로 대체하고 계속 진행

## 보안 주의
- 키를 코드·README·로그·결과 파일에 쓰지 마세요. `.env` 는 `.gitignore` 에 포함되어 커밋되지 않습니다.
- 커밋 전 `git status` 로 `.env` 가 목록에 없는지 확인하세요. 키가 노출되면 즉시 폐기 후 재발급하세요.
- 이유: 공유 시 유출 방지, 코드 수정 없이 키 교체, 과금·쿼터 사고 예방.
