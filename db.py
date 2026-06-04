import os
import psycopg2
from dotenv import load_dotenv
from queries import QUERIES, get_date_range

load_dotenv()

def fetch_metrics():
    start, end, prev_start, prev_prev_start = get_date_range()

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    curr = {}
    prev = {}
    cur = conn.cursor()

    for name, query in QUERIES.items():
        # 이번 주
        cur.execute(query.format(
            start=start, end=end,
            prev_start=prev_start, prev_prev_start=prev_prev_start
        ))
        row = cur.fetchone()
        curr[name] = row[0] if row else 0

        # 전주 (날짜를 한 주씩 밀어서 계산)
        cur.execute(query.format(
            start=prev_start, end=start,
            prev_start=prev_prev_start, prev_prev_start=prev_prev_start
        ))
        row = cur.fetchone()
        prev[name] = row[0] if row else 0

    cur.close()
    conn.close()

    return curr, prev, start, end