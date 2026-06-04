import os
import re
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

def parse_rich_text(text):
    """**굵은 글씨**를 Notion rich_text로 변환"""
    parts = []
    # **bold** 기준으로 쪼개기
    segments = re.split(r'(\*\*.*?\*\*)', text)
    for seg in segments:
        if not seg:
            continue
        if seg.startswith("**") and seg.endswith("**"):
            parts.append({
                "type": "text",
                "text": {"content": seg[2:-2]},
                "annotations": {"bold": True}
            })
        else:
            parts.append({
                "type": "text",
                "text": {"content": seg}
            })
    return parts


def line_to_block(line):
    """한 줄을 적절한 Notion 블록으로 변환"""
    stripped = line.strip()

    # 빈 줄 → 무시
    if not stripped:
        return None

    # 구분선
    if stripped == "---":
        return {"object": "block", "type": "divider", "divider": {}}

    # 제목 ###, ##, #
    if stripped.startswith("### "):
        return {"object": "block", "type": "heading_3",
                "heading_3": {"rich_text": parse_rich_text(stripped[4:])}}
    if stripped.startswith("## "):
        return {"object": "block", "type": "heading_2",
                "heading_2": {"rich_text": parse_rich_text(stripped[3:])}}
    if stripped.startswith("# "):
        return {"object": "block", "type": "heading_1",
                "heading_1": {"rich_text": parse_rich_text(stripped[2:])}}

    # 들여쓴 불릿 (하위 항목) — 앞 공백 4칸 이상이면 한 단계 들여쓰기
    indent = len(line) - len(line.lstrip())
    bullet_match = re.match(r'^[-*]\s+(.*)', stripped)
    if bullet_match:
        content = bullet_match.group(1)
        block = {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": parse_rich_text(content)}
        }
        return ("indented" if indent >= 4 else "bullet", block)

    # 그 외 → 일반 문단
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": parse_rich_text(stripped)}}


def markdown_to_blocks(content):
    """마크다운 텍스트를 Notion 블록 리스트로 변환"""
    blocks = []
    for line in content.split("\n"):
        result = line_to_block(line)
        if result is None:
            continue

        # 들여쓴 불릿이면 직전 불릿의 자식으로 넣기
        if isinstance(result, tuple):
            kind, block = result
            if kind == "indented" and blocks and \
               blocks[-1]["type"] == "bulleted_list_item":
                parent = blocks[-1]["bulleted_list_item"]
                parent.setdefault("children", []).append(block)
            else:
                blocks.append(block)
        else:
            blocks.append(result)

    return blocks


def write_to_notion(content: str, start: str, end: str):
    notion = Client(auth=os.getenv("NOTION_API_KEY"))
    parent_id = os.getenv("NOTION_PAGE_ID")

    title = f"주간 지표 브리핑 {start} ~ {end}"
    blocks = markdown_to_blocks(content)

    notion.pages.create(
        parent={"page_id": parent_id},
        properties={
            "title": {"title": [{"text": {"content": title}}]}
        },
        children=blocks
    )

    print(f"Notion 페이지 생성 완료: {title}")