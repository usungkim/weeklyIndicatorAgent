import os
import psycopg2
import statistics
from datetime import datetime, timedelta
from dotenv import load_dotenv
from queries import QUERIES, get_date_range

load_dotenv()

def fetch_metrics():
    start, end, eight_weeks_ago = get_date_range()

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    cur = conn.cursor()

    curr = {}      # 이번 주
    prev = {}      # 전주
    trends = {}    # 8주 시계열 전체

    prev_start = (datetime.strptime(start, '%Y-%m-%d')
                  - timedelta(weeks=1)).strftime('%Y-%m-%d')
    prev_prev_start = (datetime.strptime(start, '%Y-%m-%d')
                       - timedelta(weeks=2)).strftime('%Y-%m-%d')

    for name, query in QUERIES.items():
        cur.execute(query.format(
            eight_weeks_ago=eight_weeks_ago,
            start=start,
            end=end
        ))
        rows = cur.fetchall()

        weekly = {str(row[0]): float(row[1]) if row[1] else 0
                  for row in rows}
        trends[name] = weekly

        # 재충전율은 후행 지표 → 한 주 당겨서 본다 (W-2 첫충전자의 W-1 재충전)
        if name == "재충전율":
            curr[name] = weekly.get(prev_start, 0)        # W-1 주 값
            prev[name] = weekly.get(prev_prev_start, 0)   # W-2 주 값
        else:
            curr[name] = weekly.get(start, 0)
            prev[name] = weekly.get(prev_start, 0)

    cur.close()
    conn.close()

    return curr, prev, trends, start, end