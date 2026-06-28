from __future__ import annotations

import copy
from datetime import date

import pandas as pd
import streamlit as st

from ai_writer import generate_record_from_lesson, parse_lesson_outline
from docx_exporter import build_docx
from document_reader import read_uploaded_file
from schema import CHECKLIST_ITEMS, DEFAULT_RECORD, RATING_OPTIONS, SELF_CHECK_ITEMS

st.set_page_config(
    page_title="教師觀課紀錄表",
    page_icon="📋",
    layout="wide",
)


def inject_style():
    st.markdown(
        """
        <style>
        :root {
            --record-primary: #245b73;
            --record-accent: #d7833b;
            --record-ink: #1f2937;
            --record-muted: #5b6b7a;
            --record-panel: #f7fafc;
            --record-border: #d9e2ec;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1280px;
        }
        h1, h2, h3 {
            color: var(--record-ink);
            letter-spacing: 0;
        }
        h1 {
            font-size: 2.1rem;
            margin-bottom: 0.35rem;
        }
        [data-testid="stCaptionContainer"] {
            color: var(--record-muted);
        }
        .record-hero {
            border: 1px solid var(--record-border);
            background: linear-gradient(135deg, #f8fbfd 0%, #eef6f7 100%);
            padding: 1.25rem 1.35rem;
            border-radius: 8px;
            margin-bottom: 1.2rem;
        }
        .record-hero p {
            color: var(--record-muted);
            font-size: 1rem;
            margin: 0.35rem 0 0;
        }
        .record-step {
            border-left: 4px solid var(--record-accent);
            background: #fffaf4;
            padding: 0.85rem 1rem;
            border-radius: 6px;
            margin: 0.75rem 0 1rem;
            color: #5a3b1d;
        }
        div[data-testid="stDataFrameResizable"] {
            border: 1px solid var(--record-border);
            border-radius: 8px;
            overflow: hidden;
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 6px;
            min-height: 2.75rem;
            font-weight: 700;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.35rem;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 6px 6px 0 0;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def ensure_record():
    if "record" not in st.session_state:
        st.session_state.record = copy.deepcopy(DEFAULT_RECORD)
    if "lesson_text" not in st.session_state:
        st.session_state.lesson_text = ""
    if "generated" not in st.session_state:
        st.session_state.generated = False
    if "lesson_outline" not in st.session_state:
        st.session_state.lesson_outline = {}


def create_blank_record(metadata: dict[str, str]) -> dict:
    record = copy.deepcopy(DEFAULT_RECORD)
    for key, value in metadata.items():
        if value:
            record["basic_info"][key] = value
    return record


def basic_metadata_form() -> dict[str, str]:
    st.subheader("一、基本資料")
    today_roc = f"{date.today().year - 1911} 年 {date.today().month} 月 {date.today().day} 日"
    col1, col2, col3 = st.columns(3)
    with col1:
        school = st.text_input("學校", value="基隆市港西國小")
        teacher = st.text_input("授課教師", value="")
        class_name = st.text_input("教學班級", value="")
    with col2:
        observer = st.text_input("觀課教師", value="")
        subject_area = st.text_input("教學領域", value="")
        unit_name = st.text_input("教學單元", value="")
    with col3:
        lesson_minutes = st.text_input("教學時間", value="80分鐘")
        period_time = st.text_input("觀察時間／節次", value=f"{today_roc} 第   節")
        post_meeting_minutes = st.text_input("觀察後會談時間", value="40分鐘")
    return {
        "school": school,
        "teacher": teacher,
        "observer": observer,
        "class_name": class_name,
        "subject_area": subject_area,
        "unit_name": unit_name,
        "lesson_minutes": lesson_minutes,
        "period_time": period_time,
        "post_meeting_minutes": post_meeting_minutes,
    }


def edit_appendix2(record: dict):
    st.markdown("### 附表2 共同備課紀錄表")
    for field in ["教材內容", "教學目標", "學生經驗", "教學活動", "教學評量方式", "觀察的工具和觀察焦點"]:
        record["appendix2"][field] = st.text_area(field, value=record["appendix2"].get(field, ""), height=110, key=f"app2_{field}")


def edit_appendix3(record: dict):
    st.markdown("### 附表3 觀課紀錄表")
    st.caption("等第由系統依教案關鍵詞提出初步建議，請觀課教師依實際課堂表現修正。")
    rows = []
    for code, desc in CHECKLIST_ITEMS:
        rows.append({
            "代碼": code,
            "檢核重點": desc,
            "建議等第": record["appendix3"].get("ratings", {}).get(code, "普通"),
            "觀察證據／備註": record["appendix3"].get("evidence", {}).get(code, ""),
        })
    df = pd.DataFrame(rows)
    edited = st.data_editor(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "代碼": st.column_config.TextColumn(disabled=True, width="small"),
            "檢核重點": st.column_config.TextColumn(disabled=True, width="large"),
            "建議等第": st.column_config.SelectboxColumn(options=RATING_OPTIONS, required=True, width="small"),
            "觀察證據／備註": st.column_config.TextColumn(width="large"),
        },
        key="appendix3_editor",
    )
    for _, row in edited.iterrows():
        code = str(row["代碼"])
        record["appendix3"]["ratings"][code] = str(row["建議等第"])
        record["appendix3"]["evidence"][code] = str(row["觀察證據／備註"])


def edit_appendix4(record: dict):
    st.markdown("### 附表4 教學自我省思檢核表")
    cols = st.columns(2)
    for idx, item in enumerate(SELF_CHECK_ITEMS):
        with cols[idx % 2]:
            current = record["appendix4"].get("self_ratings", {}).get(item, "普通")
            index = RATING_OPTIONS.index(current) if current in RATING_OPTIONS else 1
            record["appendix4"]["self_ratings"][item] = st.selectbox(item, RATING_OPTIONS, index=index, key=f"self_{item}")
    record["appendix4"]["教學省思"] = st.text_area("◎教學省思", value=record["appendix4"].get("教學省思", ""), height=220, key="reflection_text")


def edit_appendix5(record: dict):
    st.markdown("### 附表5 議課紀錄表")
    for field in ["教學者教學優點與特色", "教學者教學待調整或改變之處", "對教學者之具體成長建議"]:
        record["appendix5"][field] = st.text_area(field, value=record["appendix5"].get(field, ""), height=150, key=f"app5_{field}")


def show_download(record: dict):
    st.markdown("---")
    st.caption("下載前請先檢查附表2至附表5內容，並依實際備課、觀課與議課情形修正。")
    docx_bytes = build_docx(record)
    unit = record["basic_info"].get("unit_name") or "公開觀課表件"
    safe_unit = "".join(c for c in unit if c not in r'\\/:*?"<>|')[:30] or "公開觀課表件"
    st.download_button(
        "⬇️ 下載 Word 觀課表件",
        data=docx_bytes,
        file_name=f"{safe_unit}_公開觀課紀錄.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
    )


def main():
    ensure_record()
    inject_style()

    st.markdown(
        """
        <div class="record-hero">
            <h1>教師觀課紀錄表</h1>
            <p>免 API Key。本機讀取教案與基本資料，自動整理附表2至附表5初稿，完成後匯出 Word。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("操作流程")
        st.write("1. 填寫基本資料")
        st.write("2. 建立空白表件，或上傳教案產生初稿")
        st.write("3. 檢查附表2至附表5內容")
        st.write("4. 下載 Word 檔")
        st.divider()
        st.caption("本版本完全在本機執行，不呼叫 OpenAI 或 Gemini。")

    st.success("目前為免 API Key 本機版：只會依你上傳的教案與輸入資訊產生初稿。")

    with st.expander("資料安全提醒", expanded=False):
        st.markdown(
            "- 建議上傳教案時避免放入學生完整姓名、身分證字號、電話、地址等個資。\n"
            "- 系統產生的是公開授課紀錄初稿，觀課教師仍需依真實課堂情形修正。\n"
            "- 若要上傳 GitHub，請不要上傳實際學生個資、API Key 或本機 secrets 檔。"
        )

    metadata = basic_metadata_form()

    st.subheader("二、建立觀課表")
    st.markdown(
        '<div class="record-step">若只是要填寫教師觀課紀錄表，可直接按「建立空白觀課表」。若已有教案檔案，請上傳後產生初稿。</div>',
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader("請上傳教案 DOCX／PDF／TXT", type=["docx", "pdf", "txt"])
    observation_notes = st.text_area(
        "觀課者補充筆記（選填，但強烈建議填）",
        placeholder="例如：學生能依教師提問分享生活經驗；小組討論時多數學生能參與，但部分學生需要教師提醒才能聚焦任務。",
        height=100,
    )

    col_a, col_b, col_c = st.columns([1.25, 1, 1])
    with col_a:
        generate = st.button("✨ 產生觀課紀錄初稿", type="primary", use_container_width=True)
    with col_b:
        blank = st.button("建立空白觀課表", use_container_width=True)
    with col_c:
        reset = st.button("清空重新開始", use_container_width=True)

    if reset:
        st.session_state.record = copy.deepcopy(DEFAULT_RECORD)
        st.session_state.lesson_text = ""
        st.session_state.lesson_outline = {}
        st.session_state.generated = False
        st.rerun()

    if blank:
        st.session_state.record = create_blank_record(metadata)
        st.session_state.lesson_text = ""
        st.session_state.lesson_outline = {}
        st.session_state.generated = True
        st.success("已建立空白觀課表，請往下填寫各附表內容。")

    if generate:
        if not uploaded:
            st.error("請先上傳教案檔案。")
        else:
            try:
                with st.spinner("正在讀取教案並產生表件初稿，請稍候……"):
                    lesson_text = read_uploaded_file(uploaded, uploaded.name)
                    if not lesson_text:
                        st.error("無法讀取教案文字。若 PDF 是掃描圖片，請先轉成可選取文字的 PDF 或改上傳 Word 檔。")
                        st.stop()
                    st.session_state.lesson_text = lesson_text
                    st.session_state.lesson_outline = parse_lesson_outline(lesson_text)
                    record = generate_record_from_lesson(
                        lesson_text=lesson_text,
                        metadata=metadata,
                        observation_notes=observation_notes,
                    )
                    # 使用者在頁面輸入的基本資料優先保留
                    for key, value in metadata.items():
                        if value:
                            st.session_state.record["basic_info"][key] = value
                    st.session_state.record = record
                    for key, value in metadata.items():
                        if value:
                            st.session_state.record["basic_info"][key] = value
                    st.session_state.generated = True
                st.success("已產生初稿，請往下檢查與修改。")
                if not st.session_state.lesson_outline.get("goals"):
                    st.warning("系統已讀取教案，但尚未辨識到「學習目標／教學目標」區塊；請檢查原教案標題或在附表2手動補上。")
            except Exception as exc:
                st.exception(exc)

    if st.session_state.generated:
        st.subheader("三、檢查與修改產生結果")
        record = st.session_state.record
        # 確保基本資料可被匯出
        for key, value in metadata.items():
            if value:
                record["basic_info"][key] = value

        if st.session_state.get("lesson_outline"):
            outline = st.session_state.lesson_outline
            with st.expander("教案解析結果", expanded=False):
                st.caption("系統會先讀取教案並擷取下列內容，再產生觀課紀錄初稿。")
                st.markdown("**教學單元**")
                st.write(outline.get("unit") or "未辨識")
                st.markdown("**學習目標／教學目標**")
                st.write(outline.get("goals") or "未辨識")
                st.markdown("**教材內容／學習內容**")
                st.write(outline.get("content") or "未辨識")
                st.markdown("**教學活動／學習活動**")
                st.write(outline.get("activity") or "未辨識")
                st.markdown("**評量方式／教學評量**")
                st.write(outline.get("assessment") or "未辨識")
                st.markdown("**教學方法與策略**")
                st.write(outline.get("strategy") or "未辨識")
                st.markdown("**學生經驗／先備經驗**")
                st.write(outline.get("prior") or "未辨識")

        tab2, tab3, tab4, tab5 = st.tabs(["附表2 共同備課", "附表3 觀課紀錄", "附表4 自我省思", "附表5 議課紀錄"])
        with tab2:
            edit_appendix2(record)
        with tab3:
            edit_appendix3(record)
        with tab4:
            edit_appendix4(record)
        with tab5:
            edit_appendix5(record)
        st.session_state.record = record
        show_download(record)
    else:
        st.info("上傳教案並按下「產生觀課紀錄初稿」後，這裡會出現可編輯的附表內容。")


if __name__ == "__main__":
    main()
