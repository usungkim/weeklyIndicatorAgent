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

    # ── Step 1. Sonnet: 지표 수치 정리 ──────────────────────────
    print("  [1/2] Sonnet: 지표 정리 중...")
    step1 = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"""
아래는 EV Infra 플랫폼의 주간 지표입니다 ({start} ~ {end}).
각 항목은 "전주 값 → 이번 주 값 (증감율)" 형식입니다.

{metrics_text}

다음을 수행하세요:
1. 각 지표의 수치 변화를 있는 그대로 정리하세요.
2. 특이하게 크거나 작은 변화(±5% 이상)를 강조 표시하세요.
3. 지표 간 연관성이 보이는 것들을 짝지어 메모하세요.
   (예: "회원가입 ▼5.9% / 첫 충전자 ▼5.7% → 유사한 하락폭")
4. 해석이나 제언은 하지 말고, 수치 정리만 하세요.
"""
        }]
    )
    summarized = step1.content[0].text

    # ── Step 2. Opus: 해석 + 제언 ───────────────────────────────
    print("  [2/2] Opus: 해석 및 제언 생성 중...")
    step2 = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=3000,
        messages=[{
            "role": "user",
            "content": f"""
당신은 EV 충전 플랫폼 'EV Infra'의 데이터 분석가입니다.

# 우리 회사의 고정된 제약 (반드시 준수)
{COMPANY_CONTEXT}

# 전주 주간회의 내용
{meeting_notes if meeting_notes else "(회의록을 불러오지 못했습니다)"}

# 이번 주 지표 정리 ({start} ~ {end})
아래는 지표 분석 결과입니다:

{summarized}

---

아래 형식으로 브리핑을 작성하세요.

## 이번 주 한 줄 요약
전체 상황을 한 문장으로. 누구나 한 번에 이해할 쉬운 말로 작성하세요.

## 주목할 변화
의미 있는 변화 2~3개를 골라 해석과 함께 서술하세요.
- 반드시 실제 수치(예: 1,346명 → 1,266명)를 본문에 포함하세요.
- 전주 회의록에 원인 단서가 있으면 명시적으로 연결하세요.
- 어려운 전문용어 대신 쉬운 말로 쓰세요.

## 가설 및 원인 추정
가능한 원인 가설을 불릿 목록으로 작성하세요. 표를 쓰지 마세요.
각 가설은 다음 형식으로:
- **가설 내용** (가능성: 높음/중간/낮음)
    - 근거: 어떤 지표나 회의록 단서에 기반하는지

## 제언 (Action Items)
실행 가능한 액션 3개를 제안하세요. 각 액션은 무엇을/왜/우선순위를 포함합니다.
**중요: 위 고정된 제약을 위반하는 액션은 절대 제안하지 마세요.**
우리가 실제로 할 수 있는 범위 안에서만 구체적으로 제안하세요.
"""
        }]
    )

    return step2.content[0].text