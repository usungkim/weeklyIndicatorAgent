import os
import anthropic
from dotenv import load_dotenv
from context import COMPANY_CONTEXT

load_dotenv()

def interpret(metrics: dict, prev_metrics: dict, meeting_notes: str,
              start: str, end: str) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def fmt(v):
        if v is None:
            return "데이터 없음"
        if isinstance(v, float):
            return f"{v:,.1f}"
        return f"{int(v):,}"

    def line(name, curr, prev):
        c = fmt(curr)
        if not prev or prev == 0:
            return f"- {name}: {c} (전주 데이터 없음)"
        change = ((curr - prev) / prev) * 100
        arrow = "▲" if change > 0 else "▼"
        return f"- {name}: {fmt(prev)} → {c} ({arrow}{abs(change):.1f}%)"

    metrics_text = "\n".join(
        line(k, v, prev_metrics.get(k)) for k, v in metrics.items()
    )

    prompt = f"""
당신은 EV 충전 플랫폼 'EV Infra'의 데이터 분석가입니다.

# 우리 회사의 고정된 제약 (반드시 준수)
{COMPANY_CONTEXT}

# 전주 주간회의 내용 (데이터 움직임의 단서)
아래는 지난주 사내 주간회의 기록입니다. 데이터 변화의 원인이
여기 적혀 있을 수 있습니다. 단, 관련 단서가 없는 경우 억지로
연결하지 말고, 데이터 자체로만 해석하세요.

{meeting_notes if meeting_notes else "(회의록을 불러오지 못했습니다)"}

# 이번 주 핵심 지표 ({start} ~ {end})
각 항목은 "전주 값 → 이번 주 값 (증감율)" 형식입니다.

{metrics_text}

---

아래 형식으로 브리핑을 작성하세요.

## 이번 주 한 줄 요약
전체 상황을 한 문장으로. 어려운 표현 대신 누구나 한 번에 이해할
쉬운 말로 작성하세요.

## 주목할 변화
의미 있는 변화 2~3개를 골라 해석과 함께 서술하세요.
- 반드시 실제 수치(예: 1,346명 → 1,266명)를 본문에 포함하세요.
- 전주 회의록에 원인 단서가 있으면 명시적으로 연결하세요.
  (예: "회의록의 PG사 변경 이슈가 이 하락과 관련 있어 보인다")
- '퍼널 상단의 하방 전달' 같은 모호한 전문용어 대신,
  '신규 가입이 줄어서 첫 충전도 같이 줄었다' 처럼 쉽게 쓰세요.

## 가설 및 원인 추정
가능한 원인 가설을 불릿 목록으로 작성하세요. 표를 쓰지 마세요.
각 가설은 다음 형식으로:
- **가설 내용** (가능성: 높음/중간/낮음)
    - 근거: 어떤 지표나 회의록 단서에 기반하는지

## 제언 (Action Items)
실행 가능한 액션 3개를 제안하세요. 각 액션은 무엇을/왜/우선순위를 포함합니다.
**중요: 위 '고정된 제약'을 위반하는 액션은 절대 제안하지 마세요.**
우리가 할 수 없는 일(CRM 자동화, 가입 채널별 분석 등)을 제안하면
브리핑 전체가 신뢰를 잃습니다. 우리가 실제로 할 수 있는 범위 안에서만
구체적으로 제안하세요.
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text