import os
import re
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

# 데이터소스 ID (collection:// 뒤의 값)
DATA_SOURCE_ID = "2d8646e5-7dfc-81f5-92ef-000ba5e9fb64"

def get_latest_meeting_notes() -> str:
    notion = Client(auth=os.getenv("NOTION_API_KEY"))

    # 데이터소스를 직접 쿼리 (생성일 최신순 1개)
    try:
        response = notion.request(
            path=f"data_sources/{DATA_SOURCE_ID}/query",
            method="POST",
            body={
                "sorts": [{"property": "생성일", "direction": "descending"}],
                "page_size": 1
            }
        )
    except Exception as e:
        print(f"  회의록 쿼리 실패: {e}")
        return ""

    results = response.get("results", [])
    if not results:
        return ""

    page = results[0]
    page_id = page["id"]
    try:
        title = page["properties"]["이름"]["title"][0]["plain_text"]
    except (KeyError, IndexError):
        title = "주간회의"

    text = _extract_blocks(notion, page_id)
    text = _filter_sections(text)   # ★ 필터 적용
    return f"## 전주 주간회의: {title}\n\n{text}"


def _extract_blocks(notion, block_id, depth=0):
    """블록을 재귀적으로 돌면서 텍스트만 추출"""
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
            rich = content.get("rich_text", [])
            line = "".join(r.get("plain_text", "") for r in rich)
            if line.strip():
                text_parts.append(line)

            if block.get("has_children"):
                child = _extract_blocks(notion, block["id"], depth + 1)
                if child:
                    text_parts.append(child)

        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")

    return "\n".join(text_parts)

def _filter_sections(text: str) -> str:
    """회의록에서 필요한 섹션만 남긴다 (토큰 절약)."""
    lines = text.split("\n")

    sections = {}
    current_key = "_intro"
    sections[current_key] = []

    top_keywords = ["프로덕트", "마케팅", "사업개발", "데이터", "경영지원"]

    for line in lines:
        stripped = line.strip()
        # "1. 프로덕트" 처럼 [숫자]. [키워드] 형식만 대제목으로 인정
        is_top = re.match(r'^\d+\.\s', stripped) and any(
            stripped.endswith(kw) or f". {kw}" in stripped
            for kw in top_keywords
        )
        if is_top:
            current_key = stripped
            sections[current_key] = [line]
        else:
            sections[current_key].append(line)

    output = []
    for key, content in sections.items():
        block = "\n".join(content)

        if "경영지원" in key:
            continue  # 통째 제외
        elif "사업개발" in key:
            output.append(_keep_subsections(block, ["로밍", "내/외부", "내외부"]))
        elif "마케팅" in key:
            output.append(_keep_subsections(block, ["타임특가", "콘텐츠", "TF", "2-3", "2-5", "2-6"]))
        else:
            output.append(block)  # 프로덕트/데이터/인트로 전체 유지

    return "\n".join(p for p in output if p.strip())


def _keep_subsections(block: str, keywords: list) -> str:
    """섹션에서 지정한 소제목 블록만 남긴다."""
    lines = block.split("\n")
    result = []
    keep = True  # 대제목 줄은 유지

    for line in lines:
        stripped = line.strip()
        # 소제목 감지: "3-1. 로밍", "2-3. 타임특가" 처럼 [숫자]-[숫자].
        if re.match(r'^\d+-\d+\.', stripped):
            keep = any(kw in stripped for kw in keywords)
        if keep:
            result.append(line)

    return "\n".join(result)