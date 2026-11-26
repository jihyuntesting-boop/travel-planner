from openai import OpenAI

from app import config
from app.services import conversation_service, summary_service

SYSTEM_TEMPLATE = """당신은 여행 경비 데이터 분석 비서입니다.

[사용자 데이터 요약]
- 데이터 기간: {period}
- 총 레코드: {count}개
- 주요 지표: {metrics}
- 최근 트렌드: {trend}

위 데이터를 기반으로 맞춤형 답변을 제공하세요. 요약에 없는 수치는 지어내지 말고 모른다고 답하세요.
금액 단위는 원입니다. 답변은 한국어로 간결하게 하세요."""


def build_system_prompt(summary: dict) -> str:
    return SYSTEM_TEMPLATE.format(
        period=summary["period"] or "데이터 없음",
        count=summary["count"],
        metrics=summary["metrics"] or "없음",
        trend=summary["trend"],
    )


def chat(message: str, conversation_id: str | None) -> dict:
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY 가 설정되지 않았습니다.")

    history: list[dict] = []
    if conversation_id:
        conv = conversation_service.get(conversation_id)
        if conv is None:
            raise LookupError("대화를 찾을 수 없습니다.")
        history = conv["messages"][-config.MAX_HISTORY_MESSAGES :]

    summary = summary_service.build_summary()  # 1) 요약 조회
    system = build_system_prompt(summary)  # 2) 시스템 프롬프트에 주입
    msgs = [{"role": "system", "content": system}, *history, {"role": "user", "content": message}]

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    resp = client.chat.completions.create(  # 3) GPT 호출
        model=config.OPENAI_MODEL, messages=msgs, max_tokens=config.MAX_TOKENS
    )
    answer = (resp.choices[0].message.content or "").strip()

    new = [{"role": "user", "content": message}, {"role": "assistant", "content": answer}]
    if conversation_id:  # 4) 자동 저장
        conversation_service.append(conversation_id, new)
    else:
        conversation_id = conversation_service.create(message[:30], new)["id"]
    return {"answer": answer, "conversation_id": conversation_id, "summary": summary}
