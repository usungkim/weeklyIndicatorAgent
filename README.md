# weeklyIndicatorAgent

EV 충전 플랫폼의 주간 핵심 지표를 자동으로 수집·해석해 Notion에 브리핑을 작성하는 Python 에이전트입니다.

매주 월요일, PostgreSQL에서 9개 지표를 쿼리하고 전주 회의록을 Notion에서 가져온 뒤 Claude API로 해석 → Notion 페이지에 자동 저장합니다.

---

## Architecture

```
main.py
├── db.py           → PostgreSQL 쿼리 실행 및 지표 수집 (9개 지표 × 8주)
├── queries.py      → 지표별 SQL 쿼리 정의
├── meeting_notes.py → 전주 Notion 회의록 불러오기
├── interpreter.py  → Claude API 2-step 해석 (Sonnet → Opus)
├── notion_writer.py → 결과를 Notion 페이지에 저장
└── context.py      → 서비스 고정 제약 조건 정의 (프롬프트 주입용)
```

---

## How It Works

### 1. 지표 수집 (`db.py` + `queries.py`)

PostgreSQL에서 아래 9개 지표를 8주 분량의 주간 시계열로 가져옵니다.

| 지표 | 설명 |
|---|---|
| 회원가입 수 | 주간 신규 가입 회원 수 |
| 카드 발급 수 | EV Pay 카드 발급 건수 |
| 카드 발급 후 미충전 (주간 신규) | 카드 발급 후 아직 충전하지 않은 유저 수 |
| 첫 충전자 수 | 해당 주에 생애 첫 충전을 한 유저 수 |
| 재충전율 | 첫 충전자 기준 다음 주 재충전 비율 (후행 지표, 1주 시차) |
| 전체 충전자 수 | 주간 충전 유저 수 |
| 첫 충전자 금액 합계 | 첫 충전자의 주간 충전 금액 합계 |
| 전체 충전 금액 | 전체 주간 충전 금액 합계 |
| 충전 건당 평균 금액 | 평균 단가 |

날짜 범위는 "막 끝난 완전한 주(지난주 월~일)" 를 기준으로 자동 계산되며, 진행 중인 주는 제외됩니다.

### 2. 8주 추세 및 통계 시그널

8주 히스토리를 기반으로 각 지표에 z-score 기반 이상 감지를 적용합니다.

- 🔴 이상치: ±2σ 초과
- 🟡 주의: ±1σ 초과
- 🟢 정상 범위

### 3. AI 해석 — 2-step Chain

**Step 1 (Claude Sonnet):** 지표 수치 정리. 이상치 강조, 노이즈 가능성 플래그, 지표 간 연관성 메모.

**Step 2 (Claude Opus):** 전주 회의록 + Sonnet 요약을 종합해 최종 브리핑 생성.

```
## 이번 주 한 줄 요약
## 주목할 변화
## 가설 및 원인 추정
## 제언 (Action Items)
```

> 회의록에 등장하는 구체적 사건(장애, 정책 변경, 이벤트 종료 등)을 지표 변화의 원인 가설로 우선 활용합니다.

### 4. Notion 저장

완성된 브리핑을 지정된 Notion 페이지 하위에 새 페이지로 자동 저장합니다.

---

## Quick Start

### 1. 환경 설정

```bash
git clone https://github.com/usungkim/weeklyIndicatorAgent.git
cd weeklyIndicatorAgent
pip install -r requirements.txt
```

### 2. `.env` 파일 생성

```bash
cp .env.example .env
```

`.env`에 아래 값을 채워넣으세요.

```env
ANTHROPIC_API_KEY=
NOTION_API_KEY=
NOTION_PAGE_ID=         # 브리핑을 저장할 Notion 페이지 ID
DB_HOST=
DB_PORT=5432
DB_NAME=
DB_USER=
DB_PASSWORD=
```

### 3. 서비스 컨텍스트 설정

`context.example.py`를 복사해 `context.py`로 만든 뒤, 자신의 서비스에 맞는 고정 제약 조건을 작성합니다. (프롬프트에 주입되어 제언의 방향을 제한합니다.)

```bash
cp context.example.py context.py
```

### 4. 실행

```bash
python main.py
# 또는
bash run_agent.sh
```

### 5. (선택) 스키마 확인

```bash
python check_schema.py
python validate_queries.py
```

---

## Automation (cron)

매주 월요일 오전 9시에 자동 실행 예시:

```cron
0 9 * * 1 /path/to/run_agent.sh >> /path/to/logs/weekly.log 2>&1
```

---

## Tech Stack

- **Language:** Python 3.x
- **Database:** PostgreSQL (SQLAlchemy)
- **AI:** Anthropic Claude API (Sonnet + Opus)
- **Output:** Notion API
- **Scheduling:** cron (`run_agent.sh`)

---

## Design Notes

- **진행 중인 주 제외:** 모든 쿼리에 `AND col < '{end}'` 조건을 명시해 불완전한 주 데이터가 섞이지 않습니다.
- **재충전율 시차:** 재충전율은 1주 후행 지표입니다. W주 브리핑의 재충전율은 W-2 첫 충전자가 W-1에 재충전한 비율이므로, 다른 지표(W vs W-1)와 기준 주가 다릅니다.
- **2-step AI Chain:** 저렴한 Sonnet으로 수치 정리를 먼저 처리해 Opus의 입력을 압축하고, Opus는 해석·제언에만 집중합니다.
- **회의록 우선 원칙:** AI 해석 시 막연한 추측보다 실제 회의록의 구체 사건을 원인 가설의 우선 근거로 사용합니다.
