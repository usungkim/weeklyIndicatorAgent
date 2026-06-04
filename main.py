from db import fetch_metrics
from meeting_notes import get_latest_meeting_notes
from interpreter import interpret
from notion_writer import write_to_notion

def run():
    print("1. 지표 수집 중...")
    metrics, prev_metrics, start, end = fetch_metrics()

    print("2. 전주 회의록 불러오는 중...")
    meeting_notes = get_latest_meeting_notes()

    print("3. 브리핑 생성 중...")
    briefing = interpret(metrics, prev_metrics, meeting_notes, start, end)
    print(briefing)

    print("4. Notion 저장 중...")
    write_to_notion(briefing, start, end)

    print("완료!")

if __name__ == "__main__":
    run()