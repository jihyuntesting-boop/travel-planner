# 여행 경비 AI 비서

내 여행 경비 기록(날짜·금액·메모)을 요약해 **시스템 프롬프트에 주입**하고, 그 데이터를 아는 AI와 대화하는 웹 서비스입니다.
"가장 많이 쓴 날은?", "요즘 지출이 늘고 있어?" 같은 질문에 내 데이터 기준으로 답합니다.

> 기존 CLI(`travel_planner.py`, Gemini + Kakao 여행지 추천)는 그대로 남아 있습니다. 아래는 새로 추가된 웹 서비스입니다.

## 기술 스택
- 백엔드: Python 3.10+, FastAPI, Pydantic, firebase-admin(Firestore), openai
- 프론트엔드: 바닐라 HTML/CSS/JavaScript (프레임워크 없음)
- 배포: Render(백엔드) + Vercel(프론트)

## 배포 URL
| 구분 | URL |
|---|---|
| 프론트(Vercel) | _배포 후 기입_ |
| 백엔드 API(Render) | _배포 후 기입_ |
| Swagger UI | `<백엔드 URL>/docs` |

> Render 무료 티어는 15분 미사용 시 잠들어 **첫 요청이 최대 1분** 걸립니다. 화면 상단에 안내 문구를 띄우고 `/health` 로 먼저 깨웁니다.

## 구조
```
backend/
  main.py                  # 앱 초기화, CORS, 라우터 등록
  app/config.py            # 환경변수
  app/db.py                # Firestore 연결 (키는 환경변수)
  app/schemas.py           # Pydantic 요청 검증
  app/routers/             # data, conversations, chat (HTTP 계층)
  app/services/            # data / summary / conversation / chat (로직 계층)
  scripts/seed.py          # 샘플 120건 입력
frontend/                  # index.html, style.css, app.js, config.js, build.sh
render.yaml                # Render 설정
```
라우터는 요청/응답·에러 변환만, 서비스는 Firestore 접근과 요약·프롬프트 로직만 맡도록 나눴습니다.
Pydantic은 날짜 형식, 금액 범위(0 이상), 문자열 길이를 서버에서 검증해 잘못된 값이 DB·프롬프트에 들어가지 않게 합니다.

## 데이터와 컨텍스트 주입
- 데이터: 여행 하루 경비 시계열 `(date, value, memo)`, 샘플 120건(`scripts/seed.py`).
- 요약(`GET /api/data/summary`): 기간, 개수, 총합/평균/중앙값/표준편차/최대/최소, 트렌드(최근 30일 평균 vs 직전 30일 평균, ±5% 이내면 유지).
- `/api/chat` 흐름: 요약 조회 → 시스템 프롬프트 템플릿에 삽입 → GPT 호출(`max_tokens=500`, 이력 최근 10개) → 대화 자동 저장.
  모델은 학습 때 내 데이터를 모르므로, 매 요청마다 요약을 프롬프트에 넣어 "내 데이터를 아는 것처럼" 답하게 하는 방식입니다.

## API
| 메서드 | 경로 | 설명 |
|---|---|---|
| POST/GET | `/api/data` | 추가 / 목록 |
| PUT/DELETE | `/api/data/{id}` | 수정 / 삭제 |
| GET | `/api/data/summary` | 요약(프롬프트 주입용) |
| GET | `/api/data/statistics` | 시계열·월별 통계(차트용, 보너스) |
| POST/GET | `/api/conversations` | 저장 / 목록(messages 미포함, `message_count` 포함) |
| GET/DELETE | `/api/conversations/{id}` | 전체 messages 조회(방식 A) / 삭제 |
| POST | `/api/chat` | AI 대화(`message`, 선택 `conversation_id`) |

Firestore 컬렉션: `data`(date, value, memo), `conversations`(title, messages[], created_at, updated_at).

## 로컬 실행
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # 값 입력
uvicorn main:app --reload   # http://localhost:8000/docs
python scripts/seed.py      # 샘플 120건 (선택)

cd ../frontend
python -m http.server 5500  # http://localhost:5500  (ALLOWED_ORIGINS 에 포함돼야 함)
```

## 환경 변수
| 이름 | 위치 | 설명 |
|---|---|---|
| `OPENAI_API_KEY` | 백엔드 | OpenAI 키 |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | 백엔드 | 서비스 계정 JSON 전체(한 줄). 또는 `FIREBASE_SERVICE_ACCOUNT_PATH` |
| `ALLOWED_ORIGINS` | 백엔드 | CORS 허용 도메인(쉼표 구분). 프론트 Vercel 도메인 |
| `OPENAI_MODEL` | 백엔드(선택) | 기본 `gpt-4o-mini` |
| `API_BASE_URL` | 프론트(Vercel) | 백엔드 주소. `build.sh` 가 `config.js` 로 주입 |

키를 코드에 두면 저장소·로그로 유출되고 교체가 어렵습니다. CORS 는 허용한 프론트 도메인만 API를 호출하게 막습니다.
`.env`, 서비스 계정 JSON은 `.gitignore` 에 포함돼 있습니다.

## 배포
- **Render**: 저장소 연결 → `render.yaml`(Root `backend`) 사용 → 환경변수 3개 입력 → `/docs` 확인.
- **Vercel**: Root Directory `frontend`, Build Command `sh build.sh`, Output Directory `.`, 환경변수 `API_BASE_URL`.
  배포 후 프론트 도메인을 Render 의 `ALLOWED_ORIGINS` 에 추가.

## 보너스 구현 현황
- ✅ 추가 지표(중앙값·표준편차), 그래프 1개(일별 추이), CSV/JSON 내보내기, 다크 모드
- ❌ Function Calling / MCP (미구현)

## 제출 스크린샷
_배포 후 아래 3장을 `docs/` 에 추가_
1. 데이터 요약이 보이는 채팅 화면 (질문+답변)
2. 데이터 관리 화면 (CRUD 1개 동작)
3. 대화 기록 화면 (불러오기 동작)

## 기존 CLI (여행지 추천)
```bash
pip install -r requirements.txt && cp .env.example .env
python travel_planner.py --date "2026-03-15"
```
Gemini + Kakao Local 로 `results/` 에 리포트를 만듭니다(키: `GEMINI_API_KEY`, `KAKAO_REST_API_KEY`).
