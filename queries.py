from datetime import datetime, timedelta

def get_date_range():
    today = datetime.now()
    # 이번 주 월요일 (진행 중, 불완전한 주)
    this_monday = today - timedelta(days=today.weekday())
    # 분석 대상 = 막 끝난 완전한 주 (지난주 월요일)  ★ 변경
    target_monday = this_monday - timedelta(weeks=1)
    # 8주 추세 시작점  ★ 변경 (target 기준)
    eight_weeks_ago = target_monday - timedelta(weeks=8)
    return (
        target_monday.strftime('%Y-%m-%d'),   # start = 분석 대상 주
        this_monday.strftime('%Y-%m-%d'),      # end = 상한선  ★
        eight_weeks_ago.strftime('%Y-%m-%d')
    )

# 각 쿼리는 week_start, value 두 컬럼을 반환 (8주치 한 번에)
QUERIES = {
    "회원가입 수": """
        SELECT
            DATE_TRUNC('week', mb_reg_datetime)::date as week_start,
            COUNT(*) as value
        FROM member
        WHERE mb_reg_datetime >= '{eight_weeks_ago}'
        AND mb_reg_datetime < '{end}'
        GROUP BY week_start
        ORDER BY week_start
    """,
    # ★ AND mb_reg_datetime < '{end}' 추가 (진행 중 주 제외)

    "카드 발급 수": """
        SELECT
            DATE_TRUNC('week', reg_date)::date as week_start,
            COUNT(*) as value
        FROM membership_card
        WHERE reg_date >= '{eight_weeks_ago}'
        AND reg_date < '{end}'
        GROUP BY week_start
        ORDER BY week_start
    """,
    # ★ AND reg_date < '{end}' 추가

    "카드 발급 후 미충전 (주간 신규)": """
        SELECT
            DATE_TRUNC('week', m.reg_date)::date as week_start,
            COUNT(DISTINCT m.mb_id) as value
        FROM membership_card m
        WHERE m.reg_date >= '{eight_weeks_ago}'
        AND m.reg_date < '{end}'
        AND NOT EXISTS (
            SELECT 1 FROM charging_history c
            WHERE c.mb_id = m.mb_id
            AND c.start_datetime >= m.reg_date
            AND c.start_datetime < '{end}'
        )
        GROUP BY week_start
        ORDER BY week_start
    """,
    # ★ AND m.reg_date < '{end}' 추가
    # ★ NOT EXISTS 안에도 c.start_datetime < '{end}' 추가 (미래 충전 무시)

    "첫 충전자 수": """
        SELECT
            first_charge.week_start,
            COUNT(DISTINCT first_charge.mb_id) as value
        FROM (
            SELECT
                mb_id,
                DATE_TRUNC('week', MIN(start_datetime))::date as week_start
            FROM charging_history
            WHERE start_datetime >= '{eight_weeks_ago}'
            AND start_datetime < '{end}'
            GROUP BY mb_id
            HAVING MIN(start_datetime) >= '{eight_weeks_ago}'
                AND mb_id NOT IN (
                    SELECT DISTINCT mb_id FROM charging_history
                    WHERE start_datetime < '{eight_weeks_ago}'
                )
        ) first_charge
        GROUP BY first_charge.week_start
        ORDER BY first_charge.week_start
    """,
    # ★ AND start_datetime < '{end}' 추가
    # ★ DATE_TRUNC에 ::date 붙이고 GROUP BY 정리 (미래날짜 차단 + 깔끔)

"재충전율": """
        SELECT
            prev.week_start,
            ROUND(
                COUNT(DISTINCT c2.mb_id) * 100.0 /
                NULLIF(COUNT(DISTINCT prev.mb_id), 0), 1
            ) as value
        FROM (
            SELECT
                DATE_TRUNC('week', start_datetime)::date as week_start,
                mb_id
            FROM charging_history
            WHERE start_datetime >= '{eight_weeks_ago}'
            AND start_datetime < '{end}'
            AND mb_id NOT IN (
                SELECT DISTINCT mb_id FROM charging_history
                WHERE start_datetime < '{eight_weeks_ago}'
            )
            GROUP BY week_start, mb_id
            HAVING MIN(start_datetime) >= '{eight_weeks_ago}'
        ) prev
        LEFT JOIN charging_history c2
            ON prev.mb_id = c2.mb_id
            AND c2.start_datetime >= (prev.week_start + INTERVAL '1 week')
            AND c2.start_datetime < (prev.week_start + INTERVAL '2 weeks')
        GROUP BY prev.week_start
        ORDER BY prev.week_start
    """,
    # ★ 서브쿼리에 AND start_datetime < '{end}' 추가
    # ★ LEFT JOIN 조건에도 c2.start_datetime < '{end}' 추가

    "전체 충전자 수": """
        SELECT
            DATE_TRUNC('week', start_datetime)::date as week_start,
            COUNT(DISTINCT mb_id) as value
        FROM charging_history
        WHERE start_datetime >= '{eight_weeks_ago}'
        AND start_datetime < '{end}'
        GROUP BY week_start
        ORDER BY week_start
    """,
    # ★ AND start_datetime < '{end}' 추가 (미래날짜 쓰레기 제거)

    "첫 충전자 금액 합계": """
        SELECT
            DATE_TRUNC('week', c.start_datetime)::date as week_start,
            COALESCE(SUM(c.charging_fee), 0) as value
        FROM charging_history c
        WHERE c.start_datetime >= '{eight_weeks_ago}'
        AND c.start_datetime < '{end}'
        AND c.mb_id NOT IN (
            SELECT DISTINCT mb_id FROM charging_history
            WHERE start_datetime < '{eight_weeks_ago}'
        )
        GROUP BY week_start
        ORDER BY week_start
    """,
    # ★ AND c.start_datetime < '{end}' 추가

    "전체 충전 금액": """
        SELECT
            DATE_TRUNC('week', start_datetime)::date as week_start,
            COALESCE(SUM(charging_fee), 0) as value
        FROM charging_history
        WHERE start_datetime >= '{eight_weeks_ago}'
        AND start_datetime < '{end}'
        GROUP BY week_start
        ORDER BY week_start
    """,
    # ★ AND start_datetime < '{end}' 추가

    "충전 건당 평균 금액": """
        SELECT
            DATE_TRUNC('week', start_datetime)::date as week_start,
            ROUND(AVG(charging_fee), 0) as value
        FROM charging_history
        WHERE start_datetime >= '{eight_weeks_ago}'
        AND start_datetime < '{end}'
        GROUP BY week_start
        ORDER BY week_start
    """
    # ★ AND start_datetime < '{end}' 추가
}