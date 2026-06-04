from datetime import datetime, timedelta

def get_date_range():
    today = datetime.now()
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(weeks=1)
    two_weeks_ago = this_monday - timedelta(weeks=2)
    three_weeks_ago = this_monday - timedelta(weeks=3)
    return (
        last_monday.strftime('%Y-%m-%d'),
        this_monday.strftime('%Y-%m-%d'),
        two_weeks_ago.strftime('%Y-%m-%d'),
        three_weeks_ago.strftime('%Y-%m-%d')
    )

QUERIES = {
    "회원가입 수": """
        SELECT COUNT(*) as value
        FROM member
        WHERE mb_reg_datetime >= '{start}' AND mb_reg_datetime < '{end}'
    """,

    "카드 발급 수": """
        SELECT COUNT(*) as value
        FROM membership_card
        WHERE reg_date >= '{start}' AND reg_date < '{end}'
    """,

    "카드 발급 후 미충전 (주간 신규)": """
        SELECT COUNT(DISTINCT m.mb_id) as value
        FROM membership_card m
        WHERE m.reg_date >= '{start}' AND m.reg_date < '{end}'
        AND NOT EXISTS (
            SELECT 1 FROM charging_history c
            WHERE c.mb_id = m.mb_id
            AND c.start_datetime >= m.reg_date
        )
    """,

    "첫 충전자 수": """
        SELECT COUNT(DISTINCT mb_id) as value
        FROM charging_history
        WHERE start_datetime >= '{start}' AND start_datetime < '{end}'
        AND mb_id NOT IN (
            SELECT DISTINCT mb_id FROM charging_history
            WHERE start_datetime < '{start}'
        )
    """,

    "재충전율": """
        SELECT
            ROUND(
                COUNT(DISTINCT c2.mb_id) * 100.0 /
                NULLIF(COUNT(DISTINCT first_chargers.mb_id), 0), 1
            ) as value
        FROM (
            SELECT DISTINCT mb_id
            FROM charging_history
            WHERE start_datetime >= '{prev_start}'
                AND start_datetime < '{start}'
                AND mb_id NOT IN (
                    SELECT DISTINCT mb_id FROM charging_history
                    WHERE start_datetime < '{prev_start}'
                )
        ) first_chargers
        LEFT JOIN charging_history c2
            ON first_chargers.mb_id = c2.mb_id
            AND c2.start_datetime >= '{start}'
    """,

    "전체 충전자 수": """
        SELECT COUNT(DISTINCT mb_id) as value
        FROM charging_history
        WHERE start_datetime >= '{start}' AND start_datetime < '{end}'
    """,

    "첫 충전자 금액 합계": """
        SELECT COALESCE(SUM(charging_fee), 0) as value
        FROM charging_history
        WHERE start_datetime >= '{start}' AND start_datetime < '{end}'
        AND mb_id NOT IN (
            SELECT DISTINCT mb_id FROM charging_history
            WHERE start_datetime < '{start}'
        )
    """,

    "전체 충전 금액": """
        SELECT COALESCE(SUM(charging_fee), 0) as value
        FROM charging_history
        WHERE start_datetime >= '{start}' AND start_datetime < '{end}'
    """,

    "충전 건당 평균 금액": """
        SELECT ROUND(AVG(charging_fee), 0) as value
        FROM charging_history
        WHERE start_datetime >= '{start}' AND start_datetime < '{end}'
    """
}