import os
import psycopg2
from dotenv import load_dotenv
from queries import QUERIES, get_date_range

load_dotenv()

start, end, prev_start, prev_prev_start = get_date_range()
print(f"이번 주: {start} ~ {end}")
print(f"전주:   {prev_start} ~ {start}")
print("=" * 60)

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)
cur = conn.cursor()

for name, query in QUERIES.items():
    print(f"\n[{name}]")
    cur.execute(query.format(
        start=start, end=end,
        prev_start=prev_start, prev_prev_start=prev_prev_start
    ))
    curr = cur.fetchone()[0]
    cur.execute(query.format(
        start=prev_start, end=start,
        prev_start=prev_prev_start, prev_prev_start=prev_prev_start
    ))
    prev = cur.fetchone()[0]
    print(f"  전주: {prev}  →  이번 주: {curr}")

cur.close()
conn.close()