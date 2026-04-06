# 🎓 多代理人 AI 論文審查與原創性檢測系統

這是一個專為學術論文打造的全方位審查系統。結合了 **多代理人協作 (Multi-Agent Collaboration)**、**AI 寫作偵測** 與 **靈活的 LLM 推論引擎 (雲端/本地)**，旨在提供專業、客觀且具備對抗性的審稿意見。

---

## 🌟 核心功能

* **🔍 AI 寫作偵測**：串接 GPTZero API，標示論文中疑似 AI 生成的段落與比例。
* **👥 多代理人交叉審查**：模擬學術研討會流程，包含：
  * **第一輪**：各委員獨立深度審核。
  * **第二輪**：委員間針對彼此觀點進行辯論與回應。
  * **第三輪**：綜合結論並給出最終裁決 (Accept/Reject)。
* **💻 靈活推論模式**：
  * **雲端 API**：支援 OpenAI GPT-4o (具備頻率限制自動重試與序列化處理)。
  * **本地落地 (Local LLM)**：支援 Llama 3 GGUF 模型，資料不外洩，具備智慧上下文截斷功能。
* **⚙️ 視覺化配置 UI**：無需手動編輯 JSON，直接在頁面修改 API Key、模型路徑與參數。
* **📥 報告匯出**：一鍵下載完整審查過程與結論為 Markdown 格式報告。

---

## 🏗️ 系統架構

系統採用模組化設計，確保高度擴充性：

* **`app.py`**：Streamlit 互動式介面，負責 UI 渲染、狀態管理與參數存取。
* **`core/orchestrator.py`**：核心協作引擎。控制審查輪數、管理並行/序列任務，並串接不同代理人的邏輯。
* **`llm/interface.py`**：統一的推論介面。封裝了 OpenAI 與 `llama-cpp-python` 的調用邏輯，並內建 Token 估算與錯誤重試。
* **`core/ai_detector.py`**：文字特徵分析模組。處理 API 請求與句子層級的高亮色彩映射。
* **`models/`**：定義論文 (`Paper`) 與審查委員 (`Reviewer`) 的資料結構與 Prompt 模板。

---

## 🚀 快速上手步驟

### 1. 環境準備

建議使用 Python 3.11+ 環境：

```powershell
# 建立虛擬環境
python -m venv .venv
# 啟動虛擬環境 (Windows)
.\.venv\Scripts\Activate.ps1
# 安裝依賴
pip install -r requirements.txt
```

> [!IMPORTANT]
> **本地模型推論 (Windows 使用者)**：
> 系統預設已安裝相容於 Windows 的 CPU 加速版本 `llama-cpp-python`。若需重新安裝，請使用官方 pre-built wheels 以避免編譯錯誤：
> `pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu`

### 2. 下載本地模型 (選用)

若要使用本地推論模式，請執行內建腳本下載 Meta-Llama-3-8B 模型：

```powershell
.\download_model.ps1
```

模型將自動存放置 `local_models/` 目錄。

### 3. 啟動系統

```powershell
streamlit run app.py
```

---

## ⚙️ 參數配置說明 (WEB UI)

啟動後，展開側邊欄並點擊 **「⚙️ 參數設定」**：

1. **雲端模式**：填入您的 `OpenAI API Key`。預設使用 `gpt-4o`。
2. **偵測器設定**：填入 `GPTZero API Key` 即可啟用真實 AI 寫作分析功能。
3. **本地模式**：可調整 `n_ctx` (上下文窗口)。針對較長論文，系統會自動在推論時截斷多餘內容以確保穩定。

---

## 📋 審查流程演示

1. **輸入論文**：上傳 `.txt` 檔案或直接貼上內文。
2. **AI 偵測**：觀察 AI 比例，深紅段落代表極高機率由 AI 生成。
3. **配置委員**：預設包含 Dr. Alan 與 Prof. Lin，您也可以自訂具備不同專業領域的新委員。
4. **執行審查**：點擊啟動。系統將自動依序進行三輪對話。
5. **匯出結果**：於頁面下方點擊「📥 匯出完整報告」獲取 Markdown 文件。

---

## 🛠️ 開發與貢獻

* **config.json**：所有設定在 UI 修改後會自動同步回此 JSON。
* **日誌觀測**：若 API 觸發 Rate Limit (429)，終端機會顯示倒數重試資訊。

---
*Created by Antigravity (Powered by Deepmind AI)*

# 多代理人論文審查系統 - 使用說明 (v2.0)

本資料夾包含了已打包的論文審查系統執行檔，現已支援 **Gemma-3** 與 **Llama-3** 雙模型選取。

## 如何執行

1. 直接點擊 **`PaperReviewSystem.exe`** 即可啟動。
2. 啟動後會自動在您的預設瀏覽器中開啟 Streamlit 介面。

## 新版功能亮點

- **雙模型預載**: 內建 Gemma-3 (7.5GB) 與 Llama-3 (4.9GB)。
- **模型選取器**: 在「⚙️ 參數設定」頁面中，點擊路徑旁的 **📂** 按鈕即可瀏覽並切換本地模型檔案。
- **自動記憶**: 選取完模型路徑並點擊「💾 儲存並套用設定」後，下次啟動將自動載入該模型。

## 檔案結構

- `PaperReviewSystem.exe`: 程式啟動檔。
- `config.json`: 系統設定檔。
- `_internal/`: 程式內部依賴資源。
- `_internal/local_models/`: 模型存放資料夾。
  - `Gemma-3-TAIDE-12b-Chat-Q4_K_M.gguf` (預設)
  - `Meta-Llama-3-8B-Instruct-Q4_K_M.gguf`

## 注意事項

- **硬體需求**: Gemma-3 需要較高的算力與顯存，若推論較慢屬正常現象。
- **自定義模型**: 您可以將自己的 `.gguf` 模型放入 `_internal/local_models`，再透過介面的 **📂** 按鈕選取路徑。

