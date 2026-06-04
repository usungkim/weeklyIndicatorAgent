import os
import statistics
import anthropic
from dotenv import load_dotenv
from context import COMPANY_CONTEXT

load_dotenv()

def interpret(metrics: dict, prev_metrics: dict, trends: dict,
              meeting_notes: str, start: str, end: str) -> str:
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

# 8주 추세 텍스트 생성
    trend_lines = []
    for name, weekly in trends.items():
        values = list(weekly.values())
        if len(values) < 3:
            continue

        curr_val = values[-1]
        avg = statistics.mean(values[:-1])
        stdev = statistics.stdev(values[:-1]) if len(values) > 2 else 0
        if stdev > 0:
            z = (curr_val - avg) / stdev
            signal = "🔴 이상치" if abs(z) > 2 else \
                     "🟡 주의" if abs(z) > 1 else "🟢 정상"
        else:
            signal = "🟢 정상"
        trend_lines.append(
            f"- {name}: 8주 평균 {avg:,.1f} / 표준편차 {stdev:,.1f} "
            f"/ 이번 주 {curr_val:,.1f} → {signal}"
        )
    trend_text = "\n".join(trend_lines)

    # ── Step 1. Sonnet: 지표 정리 ──────────────────────────
    print("  [1/2] Sonnet: 지표 정리 중...")
    step1 = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"""
아래는 EV Infra 플랫폼의 주간 지표입니다 ({start} ~ {end}).

# 이번 주 vs 전주
{metrics_text}

# 8주 추세 및 시그널 판단
(🔴 이상치: ±2σ 초과 / 🟡 주의: ±1σ 초과 / 🟢 정상 범위)
{trend_text}

다음을 수행하세요:
1. 각 지표의 수치 변화를 정리하세요.
2. 🔴 이상치 지표를 우선 강조하세요.
3. 🟢 정상 범위인데 크게 변한 것처럼 보이는 지표는 "노이즈일 가능성"을 명시하세요.
4. 지표 간 연관성이 보이는 것들을 짝지어 메모하세요.
5. 해석이나 제언은 하지 말고, 수치 정리만 하세요.
"""
        }]
    )
    summarized = step1.content[0].text

    # ── Step 2. Opus: 해석 + 제언 ───────────────────────────────
    print("  [2/2] Opus: 해석 및 제언 생성 중...")
    step2 = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": f"""
당신은 EV 충전 플랫폼 'EV Infra'의 데이터 분석가입니다.

# 우리 회사의 고정된 제약 (반드시 준수)
{COMPANY_CONTEXT}

# 전주 주간회의 내용
{meeting_notes if meeting_notes else "(회의록을 불러오지 못했습니다)"}

# 이번 주 지표 정리 ({start} ~ {end})
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
- 🔴 이상치 지표는 반드시 포함하고, 🟢 정상 범위 지표는 "노이즈일 가능성"을 언급하세요.
- 단, '재충전율'은 후행 지표라 한 주 시차를 두고 측정합니다.
  이번 브리핑의 재충전율은 '분석 대상 주의 한 주 전(W-1) 첫 충전자가
  분석 대상 주(W)에 재충전한 비율'입니다. 즉 W-2와 W-1을 비교하는 셈입니다.
  다른 지표(W vs W-1)와 기준 주가 한 주 다르다는 점을 감안해 해석하세요.
  
## 가설 및 원인 추정
가능한 원인 가설을 불릿 목록으로 작성하세요. 표를 쓰지 마세요.

**가장 중요한 원칙**: 전주 회의록에서 데이터 변화를 설명할 수 있는
구체적 사건을 먼저 찾으세요. 회의록에 실제로 일어난 일이 적혀 있다면,
그것이 막연한 추측보다 항상 우선합니다.

데이터에 영향을 줄 수 있는 사건의 종류는 다양합니다. 예를 들면:
시스템·결제 변경, 충전 인프라 장애, 제휴사 정책/요금 변화, 신규 로밍 추가,
이벤트나 프로모션의 시작·종료, 앱 업데이트, 외부 파트너 이슈 등.
이 목록에 없는 종류라도, 회의록에 적힌 사건이 지표 움직임과 시점·방향이
맞아떨어지면 근거로 삼으세요.

가설 작성 규칙:
- 회의록의 해당 내용을 구체적으로 인용하세요.
  (날짜·수치·고유명사가 있으면 그대로 가져오기)
- 회의록 사건으로 설명되는 가설은 가능성 '높음'으로 두고 맨 위에 배치하세요.
- 회의록에 단서가 없는 항목만 데이터 기반 추측으로 작성하세요.

각 가설은 다음 형식으로:
- **가설 내용** (가능성: 높음/중간/낮음)
    - 근거: 회의록 단서(있으면 구체 인용) 또는 지표 변화

## 제언 (Action Items)
실행 가능한 액션 3개를 제안하세요. 각 액션은 무엇을/왜/우선순위를 포함합니다.
**중요: 위 고정된 제약을 위반하는 액션은 절대 제안하지 마세요.**
우리가 실제로 할 수 있는 범위 안에서만 구체적으로 제안하세요.
"""
        }]
    )

    return step2.content[0].text