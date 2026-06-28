from __future__ import annotations

CHECKLIST_ITEMS = [
    ("1-1", "有組織條理呈現教材內容"),
    ("1-2", "清楚講解重要概念、原則或技能"),
    ("1-3", "提供學生適當的實作或練習"),
    ("1-4", "設計引發學生思考與討論的教學情境"),
    ("1-5", "適時歸納學習重點"),
    ("2-1", "引起並維持學生學習動機"),
    ("2-2", "善於變化教學活動或教學方法"),
    ("2-3", "教學活動融入學習策略的指導"),
    ("2-4", "教學活動轉換與銜接能順暢進行"),
    ("2-5", "有效掌握時間分配和教學節奏"),
    ("2-6", "使用有助於學生學習的教學媒材"),
    ("3-1", "口語清晰、音量適中"),
    ("3-2", "運用肢體語言，增進師生互動"),
    ("3-3", "教室走動或眼神能關照多數學生"),
    ("4-1", "教學過程中，適時檢視學生學習情形"),
    ("4-2", "學生學習成果達成預期學習目標"),
    ("5-1", "維持良好的班級秩序"),
    ("5-2", "適時增強學生的良好表現"),
    ("5-3", "妥善處理學生不當行為或偶發狀況"),
    ("6-1", "引導學生專注於學習"),
    ("6-2", "布置或安排有助學生學習的環境"),
    ("6-3", "展現熱忱的教學態度"),
]

SELF_CHECK_ITEMS = [
    "清楚呈現教材內容",
    "運用有效教學技巧",
    "應用良好溝通技巧",
    "運用學習評量評估學習成效",
    "維持良好的班級秩序以促進學習",
    "營造積極的班級氣氛",
]

RATING_OPTIONS = ["優良", "普通", "可改進", "未呈現"]

DEFAULT_RECORD = {
    "basic_info": {
        "school": "基隆市港西國小",
        "lesson_minutes": "80分鐘",
        "class_name": "",
        "period_time": "",
        "subject_area": "",
        "unit_name": "",
        "teacher": "",
        "observer": "",
        "post_meeting_minutes": "40分鐘",
    },
    "appendix2": {
        "教材內容": "",
        "教學目標": "",
        "學生經驗": "",
        "教學活動": "",
        "教學評量方式": "",
        "觀察的工具和觀察焦點": "",
    },
    "appendix3": {
        "ratings": {code: "普通" for code, _ in CHECKLIST_ITEMS},
        "evidence": {code: "" for code, _ in CHECKLIST_ITEMS},
    },
    "appendix4": {
        "self_ratings": {item: "普通" for item in SELF_CHECK_ITEMS},
        "教學省思": "",
    },
    "appendix5": {
        "教學者教學優點與特色": "",
        "教學者教學待調整或改變之處": "",
        "對教學者之具體成長建議": "",
    },
    "appendix8": {
        "學生上課狀況": "",
        "學生分組討論情形": "",
        "知識學習的情形": "",
        "綜合建議": "",
    },
    "appendix10": {
        "課堂軼事紀錄": [
            {"時間": "", "教師學習引導": "", "學生學習行為": "", "備註": ""},
            {"時間": "", "教師學習引導": "", "學生學習行為": "", "備註": ""},
            {"時間": "", "教師學習引導": "", "學生學習行為": "", "備註": ""},
        ],
        "觀課的學習": "",
    },
}


def record_schema() -> dict:
    """觀課紀錄資料結構。"""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "basic_info": {
                "type": "object",
                "additionalProperties": False,
                "properties": {k: {"type": "string"} for k in DEFAULT_RECORD["basic_info"].keys()},
                "required": list(DEFAULT_RECORD["basic_info"].keys()),
            },
            "appendix2": {
                "type": "object",
                "additionalProperties": False,
                "properties": {k: {"type": "string"} for k in DEFAULT_RECORD["appendix2"].keys()},
                "required": list(DEFAULT_RECORD["appendix2"].keys()),
            },
            "appendix3": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "ratings": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {code: {"type": "string", "enum": RATING_OPTIONS} for code, _ in CHECKLIST_ITEMS},
                        "required": [code for code, _ in CHECKLIST_ITEMS],
                    },
                    "evidence": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {code: {"type": "string"} for code, _ in CHECKLIST_ITEMS},
                        "required": [code for code, _ in CHECKLIST_ITEMS],
                    },
                },
                "required": ["ratings", "evidence"],
            },
            "appendix4": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "self_ratings": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {item: {"type": "string", "enum": RATING_OPTIONS} for item in SELF_CHECK_ITEMS},
                        "required": SELF_CHECK_ITEMS,
                    },
                    "教學省思": {"type": "string"},
                },
                "required": ["self_ratings", "教學省思"],
            },
            "appendix5": {
                "type": "object",
                "additionalProperties": False,
                "properties": {k: {"type": "string"} for k in DEFAULT_RECORD["appendix5"].keys()},
                "required": list(DEFAULT_RECORD["appendix5"].keys()),
            },
            "appendix8": {
                "type": "object",
                "additionalProperties": False,
                "properties": {k: {"type": "string"} for k in DEFAULT_RECORD["appendix8"].keys()},
                "required": list(DEFAULT_RECORD["appendix8"].keys()),
            },
            "appendix10": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "課堂軼事紀錄": {
                        "type": "array",
                        "minItems": 3,
                        "maxItems": 5,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "時間": {"type": "string"},
                                "教師學習引導": {"type": "string"},
                                "學生學習行為": {"type": "string"},
                                "備註": {"type": "string"},
                            },
                            "required": ["時間", "教師學習引導", "學生學習行為", "備註"],
                        },
                    },
                    "觀課的學習": {"type": "string"},
                },
                "required": ["課堂軼事紀錄", "觀課的學習"],
            },
        },
        "required": ["basic_info", "appendix2", "appendix3", "appendix4", "appendix5", "appendix8", "appendix10"],
    }
