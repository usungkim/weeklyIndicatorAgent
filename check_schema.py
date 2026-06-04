import os
import psycopg2
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)
cur = conn.cursor()
for table in ['membership_card', 'charging_history']:
    print(f"\n=== {table} ===")
    cur.execute(f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = '{table}'
        AND table_schema = 'public'
        ORDER BY ordinal_position
    """)
    for row in cur.fetchall():
        print(row)
cur.close()
conn.close()