from db import fetch_metrics
from meeting_notes import get_latest_meeting_notes
from interpreter import interpret
from notion_writer import write_to_notion

def run():
    print("1. 지표 수집 중...")
    metrics, prev_metrics, trends, start, end = fetch_metrics()

    print("2. 전주 회의록 불러오는 중...")
    meeting_notes = get_latest_meeting_notes()
    if not meeting_notes or len(meeting_notes) < 100:
        print("  ⚠️ 경고: 회의록을 불러오지 못했습니다 (길이 부족). 데이터만으로 브리핑합니다.")
    else:
        print(f"  ✓ 회의록 로드됨 ({len(meeting_notes)}자)")

    print("3. 브리핑 생성 중...")
    briefing = interpret(metrics, prev_metrics, trends, meeting_notes, start, end)
    print(briefing)

    print("4. Notion 저장 중...")
    write_to_notion(briefing, start, end)

    print("완료!")

if __name__ == "__main__":
    run()