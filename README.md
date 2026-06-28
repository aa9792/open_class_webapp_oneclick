# 教師觀課紀錄表產生器

這是一個免 API Key 的本機 Streamlit 網頁工具。使用者可以上傳教案檔案，系統會依教案文字與基本資料整理出可編輯的教師觀課紀錄表初稿，最後下載 Word 檔。

## 功能

- 不需要 OpenAI、Gemini 或任何外部 API Key
- 支援上傳 DOCX、PDF、TXT 教案
- 可直接建立空白觀課表手動填寫
- 可編輯附表 2、3、4、5
- 可匯出只包含附表 2 至附表 5 的 Word 觀課紀錄表

## 安裝

```bash
pip install -r requirements.txt
```

## 啟動

```bash
streamlit run app.py
```

或在 Windows 直接點選：

```text
一鍵啟動網頁.bat
```

啟動後開啟：

```text
http://localhost:8501
```

## 觀課表網址

本機使用網址：

```text
http://localhost:8501
```

這是本機網址，只能在執行此專案的電腦上開啟。若要讓其他人也能使用，請將專案部署到 Streamlit Cloud 或其他支援 Streamlit 的平台。

## HTML 分享版

專案根目錄提供 `index.html` 靜態網頁版，可部署到 GitHub Pages 後用網址分享。靜態版不需要 API Key，也不需要伺服器；支援上傳 DOCX/TXT 或貼上教案文字，產生附表 2 至附表 5，並下載 Word 可開啟的 `.doc` 表件。

公開分享網址：

```text
https://aa9792.github.io/open_class_webapp_oneclick/
```

## GitHub 安全提醒

本版本不需要 API Key。若資料夾中曾經有 `.streamlit/secrets.toml`，請不要上傳到 GitHub。

專案已提供 `.gitignore`，會忽略：

- `.streamlit/secrets.toml`
- `streamlit.out.log`
- `streamlit.err.log`
- `__pycache__/`
- 虛擬環境資料夾

上傳前也建議確認教案範例中沒有學生完整姓名、電話、地址、身分證字號或其他個資。

## 主要檔案

| 檔案 | 說明 |
|---|---|
| `app.py` | Streamlit 網頁介面 |
| `ai_writer.py` | 免 API Key 的本機教案整理邏輯 |
| `document_reader.py` | 讀取 DOCX、PDF、TXT |
| `docx_exporter.py` | 匯出 Word 觀課表 |
| `schema.py` | 表件欄位與檢核項目 |
| `requirements.txt` | Python 套件需求 |
