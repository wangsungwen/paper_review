# 多代理人論文審查系統 - 使用說明 (v3.5)

本系統是一個基於 Streamlit 的多代理人 AI 論文審查平台，支援本地 Llama-cpp (GGUF) 模型以及多種雲端 LLM 服務。透過多維度的 AI 寫作偵測與深度學術審查，為您的論文提供全方位的反饋。

---

## 🌟 核心功能說明

### 1. 🔍 三模態 AI 寫作偵測

系統整合了最前線的 AI 寫作識別技術，進化為支援三種強大運行模式：

- **Hugging Face 神經網路精準推論 (最推薦/最高效能)**：基於 `Desklib AI 偵測專用模型架構` (使用 `desklib/ai-text-detector-v1.01`) 建構的深度學習推論模式。
  - **客製化模型層**：以 PyTorch 結合 Transformer 為基底，自行添加線性分類層 (Linear Classifier) 提取隱藏狀態 (Hidden States)，達到高精準度二元分類判定。
  - **無縫即時分析**：完全免除大型語言模型的上下文長度 (Context Window) 限制，並透過 Mean Pooling 疊加演算法支援整體文本與逐句解析，提供超快速視覺化判定。
- **雲端模式 (GPTZero)**：對接全球領先的 GPTZero API，提供客觀的機率分析。
- **本地模式 (Local LLM)**：使用本地 Llama.cpp (GGUF) 大語言模型進行深度文本鑑識。
  - **超長文本支援**：可於 UI 動態調節 `n_ctx` 上下文視窗（最高支援突破 16384+ tokens）使完整論文得以無縫載入。
  - **強制 JSON 結構鎖定**：底層整合 `response_format={"type": "json_object"}`，自動降伏過度話癆的開源模型，消滅解析錯誤 (KeyError)。
  - **視覺化標記**：AI 嫌疑句會以紅色背景標示，**滑鼠懸停 (Hover)** 可隨時查看判定理由。
  - **分析摘要與數據表**：提供完整的模型寫作風格總結及詳細句點級分析數據表。

### 2. 🚀 多代理人學術審查

模擬真實的學術期刊審核流程，進行三輪深度對話：

- **第一輪：獨立審查**：多位 AI 委員根據各自專業（如硬體、演算法、數據）提供獨立意見。
- **第二輪：交叉辯論**：委員們針對彼此的意見進行討論與質疑，挖掘論文深層問題。
- **第三輪：最終裁決**：匯整所有討論，給予具體的修改建議與最終接受/拒絕判定。

### 3. 📄 多格式檔案解析

- 支援上傳 `.pdf`、`.docx` 及 `.txt` 檔案，自動提取文本內容。
- 整合 `pypdf` 與 `python-docx`，在打包環境下依然運作穩定。

---

## ⚙️ 系統設定指引

1. **☁️ 雲端 LLM**：
   - 支援依循 **OpenAI 協定** 的所有 API (OpenAI, DeepSeek, Groq, OpenRouter)。
   - 原生支援 **Google Gemini**，具備模型自動偵測功能。
2. **💻 本地 LLM**：
   - 支援 GGUF 格式。點擊 **📂** 按鈕可於硬碟中選取模型路徑。
   - 建議配置：Gemma-3-12b 或 Llama-3-8b。
3. **💾 儲存設定**：更改設定後需點擊「儲存並套用設定」方可生效。

---

## 📦 安裝說明 (Windows 11)

請確保使用 **Python 3.11/3.12** 環境，並安裝預編譯的 `llama-cpp-python` 核心：

```powershell
# 範例 (Python 3.12 用戶)
pip install https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.19/llama_cpp_python-0.3.19-cp312-cp312-win_amd64.whl
```
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu --only-binary llama-cpp-python


### 本地模型存放建議

請將下載的 `.gguf` 檔案放入 `local_models/` 資料夾中，方便程式快速讀取：

- `local_models/Gemma-3-TAIDE-12b-Chat-Q4_K_M.gguf`
- `local_models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf`

---

## ⚠️ 常見問題

- **偵測結果為 0.0%**：請檢查終端機訊息。可能是本地模型回傳格式異常，系統會自動嘗試修復，若仍失敗則會退回模擬模式。
- **解析失敗**：若 PDF 帶有密碼或為掃描圖檔，系統可能無法讀取文字，建議先轉換為純文字檔。
- **隱私聲明**：本地模式 (`local`) 數據完全不下傳，保證絕對隱私。

---
*本系統由 AI 協作開發，旨在提升學術論文的審查效率與品質。*
