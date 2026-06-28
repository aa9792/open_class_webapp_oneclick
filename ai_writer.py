from __future__ import annotations

import copy
import re
from typing import Any

from schema import CHECKLIST_ITEMS, DEFAULT_RECORD, SELF_CHECK_ITEMS


def _clean_metadata(metadata: dict[str, str]) -> dict[str, str]:
    return {key: (value or "").strip() for key, value in metadata.items()}


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _strip_label(text: str, labels: list[str]) -> str:
    value = text.strip()
    for label in labels:
        escaped = re.escape(label)
        value = re.sub(rf"^{escaped}[：:\s|｜]*", "", value).strip()
    return value.strip("；;，,、| ")


def _label_key(text: str) -> str:
    return re.sub(r"[\s：:；;，,、|｜（）()\[\]【】]+", "", text or "")


def _matches_label(text: str, labels: list[str]) -> bool:
    key = _label_key(text)
    return any(key == _label_key(label) or key.startswith(_label_key(label)) for label in labels)


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.replace("｜", "|").split("|") if cell.strip()]


def _is_probable_heading(text: str, all_labels: list[str]) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    cells = _table_cells(stripped)
    if cells and any(_matches_label(cell, all_labels) for cell in cells):
        short_cells = [cell for cell in cells if len(_label_key(cell)) <= 18]
        if len(short_cells) == len(cells):
            return True
    if _matches_label(stripped, all_labels) and len(_label_key(stripped)) <= 12:
        return True
    return bool(re.fullmatch(r"[一二三四五六七八九十\d、.．\-\s]*(?:教學|學習|評量|教材|學生|核心素養|準備活動|綜合活動)[\w\s：:、]*", stripped))


def _other_labels(labels: list[str], all_labels: list[str]) -> list[str]:
    own = {_label_key(label) for label in labels}
    return [label for label in all_labels if _label_key(label) not in own]


def _unique_items(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = re.sub(r"\s+", "", item)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _clean_display_text(text: str) -> str:
    value = re.sub(r"https?://\S+", "", text or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value.strip("；;，,、")


def _section_to_bullets(text: str, labels: list[str], max_items: int = 8) -> str:
    if not text:
        return ""

    value = text.replace("｜", "|")
    chunks: list[str] = []
    for part in re.split(r"\s*\|\s*", value):
        cleaned = _strip_label(part, labels)
        if not cleaned or cleaned in labels:
            continue
        chunks.append(cleaned)

    if not chunks:
        chunks = []
        for part in re.split(r"(?<=。)|[；;]\s*", value):
            cleaned = _strip_label(part, labels)
            if cleaned:
                chunks.append(cleaned)

    items: list[str] = []
    expanded_chunks: list[str] = []
    for chunk in chunks:
        expanded_chunks.extend(part for part in re.split(r"\n+", chunk) if part.strip())

    for chunk in expanded_chunks:
        cleaned = _clean_display_text(chunk)
        if not cleaned or cleaned in labels:
            continue
        if re.search(r"。[\s　]*[A-Za-z]+[-－][A-Za-z]+[-－]\d+", cleaned):
            for code_item in re.split(r"(?<=。)[\s　]*(?=[A-Za-z]+[-－][A-Za-z]+[-－]\d+)", cleaned):
                code_item = _clean_display_text(code_item)
                if code_item:
                    items.append(code_item)
            continue
        if (len(cleaned) > 130 or cleaned.count("。") >= 2) and "。" in cleaned:
            for sentence in re.split(r"(?<=。)", cleaned):
                sentence = _normalize_text(sentence).strip("；;，,、")
                if sentence:
                    items.append(sentence)
        else:
            items.append(cleaned)

    items = _unique_items(items)
    return "\n".join(f"• {item}" for item in items[:max_items])


def _activity_to_bullets(activity: str, max_items: int = 10) -> str:
    if not activity:
        return ""

    value = _clean_display_text(activity)
    markers = [
        "第一節",
        "第二節",
        "【準備活動】",
        "引起動機:",
        "引起動機：",
        "回顧與導入:",
        "回顧與導入：",
        "【發展活動】",
        "活動1:",
        "活動1：",
        "活動2:",
        "活動2：",
        "課堂總結與反思:",
        "課堂總結與反思：",
    ]
    pattern = "(" + "|".join(re.escape(marker) for marker in markers) + ")"
    parts = re.split(pattern, value)

    items: list[str] = []
    if len(parts) > 1:
        current = ""
        for part in parts:
            if part in markers:
                if current.strip():
                    items.append(current.strip())
                current = part
            else:
                current = (current + " " + part).strip()
        if current.strip():
            items.append(current.strip())
    else:
        for sentence in re.split(r"(?<=。)|[；;]", value):
            sentence = _clean_display_text(sentence)
            if sentence:
                items.append(sentence)

    cleaned_items = []
    for item in items:
        item = _clean_display_text(item)
        if not item or item in {"【發展活動】", "【準備活動】"}:
            continue
        cleaned_items.append(item)

    cleaned_items = _unique_items(cleaned_items)
    return "\n".join(f"• {item}" for item in cleaned_items[:max_items])


def _extract_field(patterns: list[str], text: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = _normalize_text(match.group(1))
            value = re.sub(r"[：:\s]+$", "", value)
            return value[:90]
    return ""


def _extract_row_value(labels: list[str], text: str) -> str:
    stop_labels = _other_labels(
        labels,
        [
            "領域/科目",
            "教學領域",
            "領域",
            "科目",
            "設計者",
            "實施年級",
            "教學節次",
            "教學單元",
            "單元名稱",
            "授課內容",
            "教材來源",
            "教學設備/資源",
            "教學資源",
            "教學評量",
            "學習目標",
            "教學活動",
        ],
    )
    for line in (text or "").splitlines():
        cells = _table_cells(line)
        for idx, cell in enumerate(cells):
            if _matches_label(cell, labels):
                values: list[str] = []
                inline = _strip_label(cell, labels)
                if inline and not _matches_label(inline, labels):
                    values.append(inline)
                for next_cell in cells[idx + 1 :]:
                    if _matches_label(next_cell, stop_labels):
                        break
                    if _matches_label(next_cell, labels):
                        continue
                    values.append(next_cell)
                return _normalize_text("；".join(_unique_items(values)))
    return ""


def _extract_activity_table_column(text: str, header_label: str) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    for idx, line in enumerate(lines):
        headers = _table_cells(line)
        if header_label not in headers:
            continue
        target_index = headers.index(header_label)
        values: list[str] = []
        for following in lines[idx + 1 :]:
            cells = _table_cells(following)
            if cells and _matches_label(cells[0], ["教學資源", "家電名稱"]):
                break
            if target_index < len(cells):
                value = cells[target_index].strip()
                if value and not _matches_label(value, headers):
                    values.append(value)
        return _normalize_text("；".join(_unique_items(values)))
    return ""


def _extract_inline_after_label(text: str, label: str, stop_labels: list[str]) -> str:
    pattern = re.escape(label) + r"[：:\s]*"
    match = re.search(pattern, text)
    if not match:
        return ""
    tail = text[match.end() :]
    for stop_label in stop_labels:
        stop_match = re.search(re.escape(stop_label) + r"[：:\s]*", tail)
        if stop_match:
            tail = tail[: stop_match.start()]
    return _normalize_text(tail.strip("；;，,、| "))


def _extract_resource_assessment(text: str) -> str:
    for line in (text or "").splitlines():
        if "教學評量" not in line:
            continue
        value = _extract_inline_after_label(line, "教學評量", ["教學資源", "家電名稱"])
        if value:
            return value
    return ""


def _extract_table_section(labels: list[str], text: str, max_chars: int = 1200) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    all_labels = [
        "教材內容",
        "學習內容",
        "授課內容",
        "教學目標",
        "學習目標",
        "單元目標",
        "課程目標",
        "教學活動",
        "教學流程",
        "教學過程",
        "學習活動",
        "活動流程",
        "評量方式",
        "教學評量",
        "學習評量",
        "學生經驗",
        "先備經驗",
        "起點行為",
        "核心素養",
        "學習表現",
        "準備活動",
        "綜合活動",
    ]
    stop_labels = _other_labels(labels, all_labels)

    for idx, line in enumerate(lines):
        cells = _table_cells(line)
        if not cells:
            continue

        for cell_index, cell in enumerate(cells):
            if not _matches_label(cell, labels):
                continue

            collected: list[str] = []
            inline = _strip_label(cell, labels)
            if inline and not _matches_label(inline, labels):
                collected.append(inline)

            for following_cell in cells[cell_index + 1 :]:
                if _matches_label(following_cell, stop_labels):
                    break
                cleaned = _strip_label(following_cell, labels)
                if cleaned and not _matches_label(cleaned, labels):
                    collected.append(cleaned)

            if not collected:
                for following_line in lines[idx + 1 : idx + 10]:
                    if _is_probable_heading(following_line, all_labels):
                        break
                    cleaned = _strip_label(following_line, labels)
                    if cleaned:
                        collected.append(cleaned)

            value = _normalize_text("；".join(collected))
            if value:
                return value[:max_chars]
    return ""


def _extract_section(title_patterns: list[str], text: str, max_chars: int = 1200) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    titles = "|".join(title_patterns)
    stop_words = r"教學目標|學習目標|教材內容|教學活動|教學流程|教學過程|學習活動|活動流程|評量方式|教學評量|學生經驗|先備經驗|核心素養|學習表現|學習內容|準備活動|綜合活動"

    for idx, line in enumerate(lines):
        if re.search(titles, line):
            collected: list[str] = []
            remainder = re.sub(rf"^.*?(?:{titles})[：:\s]*", "", line).strip()
            remainder = re.split(stop_words, remainder, maxsplit=1)[0].strip()
            if remainder and not re.fullmatch(r"[一二三四五六七八九十、.．\d\s-]+", remainder):
                collected.append(remainder)
            if line.count("|") < 2:
                for following in lines[idx + 1 : idx + 8]:
                    if re.search(stop_words, following) and collected:
                        break
                    collected.append(following)
            value = _normalize_text("；".join(collected))
            if value:
                return value[:max_chars]
    return ""


def parse_lesson_outline(lesson_text: str) -> dict[str, str]:
    """先閱讀教案文字，擷取產生觀課紀錄所需的主要區塊。"""
    activity = _extract_activity_table_column(lesson_text, "教學活動內容及實施方式")
    assessment = _extract_activity_table_column(lesson_text, "教學評量") or _extract_resource_assessment(lesson_text)
    strategy = _extract_activity_table_column(lesson_text, "教學方法與策略")
    content = _extract_table_section(["教材內容", "學習內容", "授課內容"], lesson_text) or _extract_section([r"教材內容", r"學習內容", r"授課內容"], lesson_text)
    material_source = _extract_row_value(["教材來源", "教學設備/資源", "教學資源"], lesson_text)
    if material_source:
        content = "\n".join(part for part in [content, f"教材與設備資源：{material_source}"] if part)
    return {
        "unit": _extract_row_value(["教學單元", "單元名稱", "授課內容"], lesson_text)
        or _extract_field([r"教學單元(?:名稱)?[：:\s]+([^\n]+)", r"單元名稱[：:\s]+([^\n]+)", r"授課內容[：:\s]+([^\n]+)"], lesson_text),
        "area": _extract_row_value(["領域/科目", "教學領域", "領域", "科目"], lesson_text)
        or _extract_field([r"教學領域[：:\s]+([^\n]+)", r"領域[：:\s]+([^\n]+)", r"科目[：:\s]+([^\n]+)"], lesson_text),
        "goals": _extract_table_section(["教學目標", "學習目標", "單元目標", "課程目標"], lesson_text)
        or _extract_section([r"教學目標", r"學習目標", r"單元目標", r"課程目標"], lesson_text),
        "content": content,
        "activity": activity
        or _extract_table_section(["教學活動內容及實施方式", "教學活動", "教學流程", "活動流程", "教學過程", "學習活動"], lesson_text)
        or _extract_section([r"教學活動", r"教學流程", r"活動流程", r"教學過程", r"學習活動"], lesson_text),
        "assessment": assessment
        or _extract_table_section(["評量方式", "教學評量", "學習評量"], lesson_text)
        or _extract_section([r"評量方式", r"教學評量", r"學習評量"], lesson_text),
        "strategy": strategy,
        "prior": _extract_table_section(["學生經驗", "先備經驗", "起點行為"], lesson_text)
        or _extract_section([r"學生經驗", r"先備經驗", r"起點行為"], lesson_text),
    }


def _lesson_keywords(text: str) -> set[str]:
    keyword_groups = {
        "討論": ["討論", "小組", "分享", "合作", "發表"],
        "實作": ["實作", "操作", "演練", "任務", "學習單"],
        "探究": ["探究", "觀察", "提問", "問題", "情境"],
        "評量": ["評量", "檢核", "回饋", "成果", "反思"],
        "媒材": ["影片", "簡報", "圖片", "教具", "媒材", "資訊"],
    }
    found: set[str] = set()
    for label, words in keyword_groups.items():
        if any(word in text for word in words):
            found.add(label)
    return found


def _fallback(value: str, fallback: str = "教案未明確提供") -> str:
    return value.strip() if value and value.strip() else fallback


def _missing(label: str) -> str:
    return f"教案未明確提供「{label}」資料，請依實際教案或觀課情形補充。"


def _brief(text: str, limit: int = 180) -> str:
    value = _normalize_text(text)
    return value[:limit] + ("..." if len(value) > limit else "")


def _source_text(label: str, text: str) -> str:
    return f"依教案「{label}」：{_brief(text)}" if text else _missing(label)


def _source_bullets(label: str, text: str, labels: list[str]) -> str:
    bullets = _section_to_bullets(text, labels)
    return bullets or f"• {_missing(label)}"


def _best_source(sources: list[tuple[str, str]]) -> tuple[str, str]:
    for label, value in sources:
        if value:
            return label, value
    return sources[0][0], ""


def _rating_from_source(source: str, preferred: bool = False) -> str:
    if not source:
        return "未呈現"
    return "優良" if preferred else "普通"


def _activity_rows(activity: str) -> list[dict[str, str]]:
    items = _select_event_items(activity, max_items=5)
    if not items:
        return [
            {"時間": "", "教師學習引導": _missing("教學活動"), "學生學習行為": _missing("學生學習行為"), "備註": "請依實際觀課補充。"},
            {"時間": "", "教師學習引導": _missing("教學活動"), "學生學習行為": _missing("學生學習行為"), "備註": "請依實際觀課補充。"},
            {"時間": "", "教師學習引導": _missing("教學活動"), "學生學習行為": _missing("學生學習行為"), "備註": "請依實際觀課補充。"},
        ]

    labels = ["課程前段", "課程中段", "課程後段", "延伸活動", "總結活動"]
    rows: list[dict[str, str]] = []
    for idx, item in enumerate(items[:5]):
        rows.append(
            {
                "時間": labels[idx] if idx < len(labels) else "",
                "教師學習引導": _teacher_action_from_activity(item),
                "學生學習行為": _student_behavior_from_activity(item),
                "備註": "由教案活動推得，請觀課時補上實際學生語句、作品或小組互動證據。",
            }
        )
    while len(rows) < 3:
        rows.append({"時間": "", "教師學習引導": _missing("教學活動"), "學生學習行為": _missing("學生學習行為"), "備註": "請依實際觀課補充。"})
    return rows


def _plain_activity_summary(activity: str, limit: int = 260) -> str:
    items = _select_event_items(activity, max_items=6)
    summaries: list[str] = []
    for item in items:
        if item.startswith(("第一節", "第二節")):
            continue
        elif item.startswith("【準備活動】"):
            continue
        elif item.startswith(("引起動機:", "引起動機：")):
            summaries.append("引起動機")
        elif item.startswith(("回顧與導入:", "回顧與導入：")):
            summaries.append("回顧與導入")
        elif item.startswith(("課堂總結與反思:", "課堂總結與反思：")):
            summaries.append("課堂總結與反思")
        elif re.match(r"活動\d+[:：]", item):
            title = re.split(r"\s+(?:教師|學生|播放|影片|利用|回顧|說明)|[「【]", item, maxsplit=1)[0]
            summaries.append(title.strip())
        elif len(item) <= 35:
            summaries.append(item)
    if not summaries:
        summaries = items[:4]
    return _brief("、".join(_unique_items(summaries)), limit)


def _meaningful_activity_items(activity: str, max_items: int = 8) -> list[str]:
    bullets = _activity_to_bullets(activity, max_items=14)
    raw_items = [line.lstrip("• ").strip() for line in bullets.splitlines() if line.strip()]
    items: list[str] = []
    for item in raw_items:
        if item in {"第一節", "第二節", "【準備活動】"}:
            continue
        if item.startswith("【準備活動】 課堂準備"):
            continue
        items.append(item)
    return items[:max_items]


def _select_event_items(activity: str, max_items: int = 5) -> list[str]:
    items = _meaningful_activity_items(activity, max_items=12)
    priority_rules = [
        (["引起動機", "回顧與導入"], ["slido", "短片", "提問"]),
        (["瓦特", "1度電", "一度電"], ["關係學習", "試算", "1000瓦"]),
        (["家電耗能", "電力檢測儀", "測量"], ["學生分組", "完成紀錄表", "安全接線"]),
        (["風力發電"], ["組裝", "學生分組", "LED", "小馬達"]),
        (["課堂總結", "回顧核心", "反思", "節能"], ["永續", "小行動", "能量的轉換"]),
    ]

    selected: list[str] = []
    for patterns, preferred in priority_rules:
        candidates = [item for item in items if item not in selected and any(pattern in item for pattern in patterns)]
        if not candidates:
            continue

        def score(item: str) -> tuple[int, int, int]:
            preferred_hits = sum(1 for word in preferred if word in item)
            activity_bonus = 1 if re.match(r"活動\d+[:：]", item) else 0
            summary_bonus = 1 if item.startswith("課堂總結") or "回顧核心" in item else 0
            return preferred_hits, activity_bonus + summary_bonus, min(len(item), 400)

        selected.append(max(candidates, key=score))

    for item in items:
        if len(selected) >= max_items:
            break
        if item not in selected:
            selected.append(item)
    return selected[:max_items]


def _student_behavior_from_activity(item: str) -> str:
    if item.startswith("課堂總結") or "回顧核心學習" in item:
        return "學生可分享實測或實作結果，回顧功率、耗電量與能源轉換概念，觀課時宜記錄學生是否能提出具體節能行動並說明理由。"
    if item.startswith(("引起動機", "回顧與導入")):
        return "學生可透過即時回應、口頭回答或觀看影片連結生活用電經驗，觀課時宜記錄學生提出的家電例子、耗電判斷與追問情形。"
    if any(word in item for word in ["瓦特", "一度電", "1度電", "度電"]):
        return "學生可透過教師提問、影片或簡易試算理解瓦特與一度電的關係，觀課時宜記錄學生是否能以生活例子說明功率與耗電量。"
    if any(word in item for word in ["電力檢測儀", "測量", "耗能實測", "完成紀錄表", "安全接線"]):
        return "學生可分組操作電力檢測儀、讀取功率數值並完成紀錄，觀課時宜記錄小組分工、數據判讀與討論品質。"
    if any(word in item for word in ["風力發電", "組裝", "LED", "扇葉", "小馬達"]):
        return "學生可透過組裝與測試風力發電機理解能量轉換，觀課時宜記錄學生操作安全、問題解決與概念連結情形。"
    if any(word in item for word in ["slido", "回答", "提問", "你知道", "為什麼"]):
        return "學生可透過即時回應或口頭回答連結生活用電經驗，觀課時宜記錄學生是否能提出具體家電或用電情境。"
    if any(word in item for word in ["分享", "發表", "總結", "反思", "節電", "永續"]):
        return "學生可分享觀察結果與節能想法，觀課時宜記錄學生是否能用學到的概念說明自己的判斷。"
    if any(word in item for word in ["影片", "短片"]):
        return "學生可透過影片建立先備概念，觀課時宜記錄學生觀看後的提問、回應與概念連結。"
    return "學生可依活動任務參與討論、操作或回應，觀課時宜補充實際學生語句、作品或小組表現。"


def _teacher_action_from_activity(item: str) -> str:
    clean = _brief(_clean_display_text(item), 170)
    if item.startswith(("引起動機", "回顧與導入")):
        return f"依教案安排，教師以問題引導或影片導入建立學習情境：{clean}"
    if re.match(r"活動\d+[:：]", item):
        return f"依教案主要活動，教師安排任務與操作流程：{clean}"
    if item.startswith("課堂總結"):
        return f"依教案總結活動，教師引導學生回顧概念並進行反思：{clean}"
    return f"依教案教學活動，教師進行學習引導：{clean}"


def _reflection_paragraph(goals: str, content: str, activity: str, assessment: str, strategy: str) -> str:
    paragraphs: list[str] = []
    if goals:
        paragraphs.append(
            f"本課以「{_brief(goals, 140)}」為主要學習目標，課程設計能扣合學生對能源與生活用電的理解，並將概念學習延伸到日常節能行動。"
        )
    if content or activity:
        paragraphs.append(
            f"從教案安排來看，教材內容聚焦於「{_brief(content, 120)}」，並透過{_plain_activity_summary(activity, 180) or '教案所列教學活動'}引導學生由生活情境進入探究與實作。這樣的活動設計有助於學生在操作、討論與反思中建構概念。"
        )
    if strategy or assessment:
        paragraphs.append(
            f"教案中規劃的教學方法與策略包含「{_brief(strategy, 120) if strategy else '教案未明確提供'}」，評量方式則包含「{_brief(assessment, 120) if assessment else '教案未明確提供'}」。課後可進一步檢視學生是否能以自己的語言說明學習重點，並依實際學習證據調整提問層次、操作時間與回饋方式。"
        )
    return "\n\n".join(paragraphs) if paragraphs else _missing("教學省思")


def _discussion_strengths(goals: str, activity: str, strategy: str) -> str:
    pieces: list[str] = []
    if goals:
        pieces.append(f"本課教學目標明確，能聚焦於{_brief(goals, 150)}")
    if activity:
        pieces.append(f"教學活動以{_plain_activity_summary(activity, 180)}為主軸，能讓學生從生活用電經驗進入實作與討論")
    if strategy:
        pieces.append(f"教案也安排{_brief(strategy, 120)}等策略，提供學生參與、操作與表達的機會")
    if not pieces:
        return _missing("教學優點與特色")
    return "；".join(pieces) + "。整體而言，課程能將能源概念與學生生活經驗連結，具備探究、實作與反思並重的特色。"


def _discussion_adjustments(assessment: str, activity: str) -> str:
    pieces: list[str] = []
    if assessment:
        pieces.append(f"教案已規劃{_brief(assessment, 140)}等評量方式，議課時可進一步檢視這些評量是否能充分呈現學生對概念、技能與態度的學習成效")
    else:
        pieces.append(_missing("評量方式／教學評量"))
    if activity:
        pieces.append("由於活動包含影片導入、儀器測量、小組操作與成果討論，建議留意各活動時間分配、轉換銜接與學生操作安全提醒是否足夠清楚")
    pieces.append("若實際課堂中學生反應差異較大，可再補強任務分工、學習單提示或教師巡視回饋。")
    return "。".join(pieces)


def _discussion_growth(goals: str, activity: str, assessment: str, note: str) -> str:
    pieces = [
        "建議後續可將觀課重點放在學生是否能達成教案學習目標，以及能否在實作後說明能源轉換、耗電量與節能行動之間的關係。",
    ]
    if activity:
        pieces.append(f"觀課時可對照教案活動「{_plain_activity_summary(activity, 160)}」，記錄學生在小組討論、操作測量、組裝實作與口頭發表中的具體表現。")
    if assessment:
        pieces.append(f"議課時可再檢視「{_brief(assessment, 120)}」是否足以回應學習目標，並思考是否需要增加學生反思、同儕分享或成果檢核規準。")
    if note:
        pieces.append(f"觀課者補充筆記指出：{_brief(note, 160)}")
    return "\n".join(pieces)


def _appendix8_student_status(activity: str, strategy: str) -> str:
    items = _meaningful_activity_items(activity, max_items=4)
    activity_summary = "、".join(_plain_activity_summary(activity, 160).split("、")[:5])
    strategy_text = _brief(strategy, 120) if strategy else "教案未明確提供"
    if not items:
        return _missing("學生上課狀況")
    return (
        f"依教案活動安排，學生會經歷{activity_summary}等任務，並在問題引導、操作演示或小組合作中參與學習。"
        f"觀課時可重點記錄學生是否能專注回應教師提問、投入家電耗能測量或風力發電實作，並觀察是否能依任務要求完成紀錄、討論與分享。"
        f"教案所列教學策略包含「{strategy_text}」，可作為判斷學生投入程度與課堂互動品質的依據。"
    )


def _appendix8_group_discussion(activity: str) -> str:
    if not activity:
        return _missing("分組討論或合作學習")
    if not any(word in activity for word in ["小組", "分組", "討論", "合作"]):
        return "教案未明確呈現小組討論安排；若課堂實施時有分組任務，請補充學生互動、分工與討論內容。"
    return (
        "教案安排學生分組使用電力檢測儀測量家電耗電量，並進行風力發電機組裝或相關實作。"
        "觀課時可記錄各組是否能完成分工、共同讀取數據、討論耗電差異，並能把操作結果連結到瓦特、一度電與能源轉換概念。"
        "也可觀察小組內是否有學生主導、等待、離題或互相協助的情形，作為議課時討論合作學習品質的依據。"
    )


def _appendix8_knowledge_learning(goals: str, content: str, activity: str, assessment: str) -> str:
    return (
        f"教案學習目標聚焦於「{_brief(goals, 180) if goals else '教案未明確提供'}」，教材內容包含「{_brief(content, 160) if content else '教案未明確提供'}」。"
        "從活動設計來看，學生可透過家電耗能實測理解功率與耗電量，也可透過風力發電實作理解能量轉換。"
        f"評量方式規劃為「{_brief(assessment, 140) if assessment else '教案未明確提供'}」，觀課時宜蒐集學生口頭回答、學習單、操作紀錄與小組成果，判斷學生是否真正理解概念而非只完成操作。"
    )


def _appendix8_suggestion(goals: str, activity: str, assessment: str) -> str:
    return (
        "建議觀課時以學生學習證據為核心，對照教案學習目標檢視學生是否能說明瓦特、一度電、家電耗能與風力發電的關係。"
        "若發現學生能操作但無法說明原理，可在議課時討論是否增加教師歸納、同儕分享或概念檢核。"
        "若活動時間較緊，建議優先保留操作後的數據解讀與反思提問，讓實作經驗能轉化為可說明、可遷移的能源素養。"
    )


def _appendix10_learning(goals: str, activity: str, assessment: str, strategy: str) -> str:
    return (
        "本次觀課可聚焦學生學習如何由生活用電經驗進入能源概念理解。"
        f"教案目標為「{_brief(goals, 160) if goals else '教案未明確提供'}」，活動設計包含{_plain_activity_summary(activity, 160) or '教案所列活動'}，"
        "因此觀課時可特別記錄學生在提問回應、家電耗能測量、風力發電實作與課堂反思中的學習轉變。"
        f"教案評量方式為「{_brief(assessment, 120) if assessment else '教案未明確提供'}」，教學策略包含「{_brief(strategy, 120) if strategy else '教案未明確提供'}」。"
        "議課時可進一步討論這些評量是否足以看見學生的概念理解、操作能力與節能態度。"
    )


def generate_record_from_lesson(
    lesson_text: str,
    metadata: dict[str, str],
    observation_notes: str = "",
) -> dict[str, Any]:
    """依教案文字與使用者輸入資料產生本機版觀課紀錄初稿，不呼叫任何外部 API。"""
    data = copy.deepcopy(DEFAULT_RECORD)
    metadata = _clean_metadata(metadata)
    normalized = _normalize_text(lesson_text)
    keywords = _lesson_keywords(lesson_text)

    lesson_outline = parse_lesson_outline(lesson_text)
    guessed_unit = lesson_outline["unit"]
    guessed_area = lesson_outline["area"]
    guessed_goal = lesson_outline["goals"]
    guessed_content = lesson_outline["content"]
    guessed_activity = lesson_outline["activity"]
    guessed_assessment = lesson_outline["assessment"]
    guessed_strategy = lesson_outline.get("strategy", "")
    guessed_prior = lesson_outline["prior"]

    data["basic_info"].update(
        {
            "school": metadata.get("school") or "基隆市港西國小",
            "lesson_minutes": metadata.get("lesson_minutes") or "80分鐘",
            "class_name": metadata.get("class_name") or "教案未明確提供",
            "period_time": metadata.get("period_time") or "教案未明確提供",
            "subject_area": metadata.get("subject_area") or guessed_area or "教案未明確提供",
            "unit_name": metadata.get("unit_name") or guessed_unit or "教案未明確提供",
            "teacher": metadata.get("teacher") or "教案未明確提供",
            "observer": metadata.get("observer") or "教案未明確提供",
            "post_meeting_minutes": metadata.get("post_meeting_minutes") or "40分鐘",
        }
    )

    lesson_preview = normalized[:220]
    content_text = _section_to_bullets(guessed_content, ["教材內容", "學習內容", "授課內容"])
    goal_text = _section_to_bullets(guessed_goal, ["教學目標", "學習目標"])
    data["appendix2"] = {
        "教材內容": _fallback(content_text, f"• 依教案文字整理，本課教材重點包含：{lesson_preview}"),
        "教學目標": _fallback(goal_text, f"• {_missing('學習目標／教學目標')}"),
        "學生經驗": _source_text("學生經驗／先備經驗", guessed_prior),
        "教學活動": _activity_to_bullets(guessed_activity) or f"• {_missing('教學活動／學習活動')}",
        "教學評量方式": _source_text("評量方式／教學評量", guessed_assessment),
        "觀察的工具和觀察焦點": "\n".join(
            [
                f"• 觀察學生是否達成教案學習目標：{_brief(guessed_goal)}" if guessed_goal else f"• {_missing('學習目標／教學目標')}",
                f"• 觀察學生在教案活動中的參與與表現：{_brief(guessed_activity)}" if guessed_activity else f"• {_missing('教學活動／學習活動')}",
                f"• 依教案評量方式蒐集學習證據：{_brief(guessed_assessment)}" if guessed_assessment else f"• {_missing('評量方式／教學評量')}",
                f"• 觀察教學方法與策略是否支持學習：{_brief(guessed_strategy)}" if guessed_strategy else f"• {_missing('教學方法與策略')}",
            ]
        ),
    }

    checklist_sources = {
        "1-1": [("教材內容／學習內容", guessed_content), ("學習目標／教學目標", guessed_goal)],
        "1-2": [("學習目標／教學目標", guessed_goal), ("教材內容／學習內容", guessed_content)],
        "1-3": [("教學活動／學習活動", guessed_activity)],
        "1-4": [("教學活動／學習活動", guessed_activity), ("學習目標／教學目標", guessed_goal)],
        "1-5": [("教學活動／學習活動", guessed_activity), ("評量方式／教學評量", guessed_assessment)],
        "2-1": [("學生經驗／先備經驗", guessed_prior), ("教學活動／學習活動", guessed_activity)],
        "2-2": [("教學方法與策略", guessed_strategy), ("教學活動／學習活動", guessed_activity)],
        "2-3": [("教學方法與策略", guessed_strategy), ("教學活動／學習活動", guessed_activity), ("學習目標／教學目標", guessed_goal)],
        "2-4": [("教學活動／學習活動", guessed_activity), ("教學方法與策略", guessed_strategy)],
        "2-5": [("教學活動／學習活動", guessed_activity)],
        "2-6": [("教學活動／學習活動", guessed_activity), ("教材內容／學習內容", guessed_content), ("教學方法與策略", guessed_strategy)],
        "3-1": [("教師口語與說明方式", "")],
        "3-2": [("教學方法與策略", guessed_strategy), ("教學活動／學習活動", guessed_activity)],
        "3-3": [("教師巡視與關照學生方式", "")],
        "4-1": [("評量方式／教學評量", guessed_assessment)],
        "4-2": [("學習目標／教學目標", guessed_goal), ("評量方式／教學評量", guessed_assessment)],
        "5-1": [("班級經營與秩序安排", "")],
        "5-2": [("回饋或增強設計", guessed_assessment if "回饋" in guessed_assessment else "")],
        "5-3": [("偶發狀況處理方式", "")],
        "6-1": [("教學活動／學習活動", guessed_activity)],
        "6-2": [("教材內容／學習內容", guessed_content), ("教學活動／學習活動", guessed_activity)],
        "6-3": [("教師教學態度或熱忱", "")],
    }
    preferred_codes = set()
    if "實作" in keywords:
        preferred_codes.update({"1-3", "2-2", "2-6"})
    if "討論" in keywords:
        preferred_codes.update({"1-4", "3-2", "6-1"})
    if "探究" in keywords:
        preferred_codes.update({"1-4", "2-1", "2-3"})
    if "評量" in keywords:
        preferred_codes.update({"4-1", "4-2"})

    for code, _item in CHECKLIST_ITEMS:
        label, source = _best_source(checklist_sources.get(code, [("教案資料", "")]))
        data["appendix3"]["ratings"][code] = _rating_from_source(source, code in preferred_codes)
        data["appendix3"]["evidence"][code] = _source_text(label, source)

    for item in SELF_CHECK_ITEMS:
        if item == "清楚呈現教材內容":
            data["appendix4"]["self_ratings"][item] = _rating_from_source(guessed_content)
        elif item == "運用有效教學技巧":
            data["appendix4"]["self_ratings"][item] = _rating_from_source(guessed_activity)
        elif item == "運用學習評量評估學習成效":
            data["appendix4"]["self_ratings"][item] = _rating_from_source(guessed_assessment)
        elif item == "應用良好溝通技巧":
            data["appendix4"]["self_ratings"][item] = _rating_from_source(guessed_activity)
        else:
            data["appendix4"]["self_ratings"][item] = "未呈現"
    data["appendix4"]["教學省思"] = _reflection_paragraph(
        goals=guessed_goal,
        content=guessed_content,
        activity=guessed_activity,
        assessment=guessed_assessment,
        strategy=guessed_strategy,
    )

    note = observation_notes.strip()
    data["appendix5"] = {
        "教學者教學優點與特色": _discussion_strengths(
            goals=guessed_goal,
            activity=guessed_activity,
            strategy=guessed_strategy,
        ),
        "教學者教學待調整或改變之處": _discussion_adjustments(
            assessment=guessed_assessment,
            activity=guessed_activity,
        ),
        "對教學者之具體成長建議": _discussion_growth(
            goals=guessed_goal,
            activity=guessed_activity,
            assessment=guessed_assessment,
            note=note,
        ),
    }

    return data


def demo_record(lesson_text: str, metadata: dict[str, str], observation_notes: str = "") -> dict[str, Any]:
    """Backward-compatible alias for older code paths."""
    return generate_record_from_lesson(lesson_text, metadata, observation_notes)
