import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

# 주간회의 데이터소스 ID (DB 안의 collection ID)
MEETING_DB_ID = "2d8646e5-7dfc-81f5-92ef-000ba5e9fb64"

def get_latest_meeting_notes() -> str:
    notion = Client(auth=os.getenv("NOTION_API_KEY"))

    # 주간회의 DB 안의 페이지들을 검색 (최근 수정순)
    response = notion.search(
        query="주간회의",
        sort={"direction": "descending", "timestamp": "last_edited_time"},
        filter={"property": "object", "value": "page"},
        page_size=5
    )

    # 결과 중 주간회의 DB 소속 페이지만 골라 가장 최근 것 선택
    target = None
    for page in response["results"]:
        parent = page.get("parent", {})
        if parent.get("database_id", "").replace("-", "") == MEETING_DB_ID.replace("-", ""):
            target = page
            break

    if not target:
        return ""

    page_id = target["id"]
    try:
        title = target["properties"]["이름"]["title"][0]["plain_text"]
    except (KeyError, IndexError):
        title = "주간회의"

    text = _extract_blocks(notion, page_id)
    return f"## 전주 주간회의: {title}\n\n{text}"


def _extract_blocks(notion, block_id, depth=0):
    """블록을 재귀적으로 돌면서 텍스트만 추출 (최대 깊이 제한)"""
    if depth > 3:
        return ""

    text_parts = []
    cursor = None

    while True:
        kwargs = {"block_id": block_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor

        resp = notion.blocks.children.list(**kwargs)

        for block in resp["results"]:
            btype = block["type"]
            content = block.get(btype, {})

            # rich_text가 있는 블록이면 텍스트 추출
            rich = content.get("rich_text", [])
            line = "".join(r.get("plain_text", "") for r in rich)
            if line.strip():
                text_parts.append(line)

            # 하위 블록이 있으면 재귀
            if block.get("has_children"):
                child = _extract_blocks(notion, block["id"], depth + 1)
                if child:
                    text_parts.append(child)

        if not resp.get("has_more"):
            break
        cursor = resp["start_cursor"]

    return "\n".join(text_parts)