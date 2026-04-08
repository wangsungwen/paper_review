# 多代理人論文審查系統 - 使用說明 (v3.0)

本系統是一個基於 Streamlit 的多代理人 AI 論文審查平台，支援本地 Llama-cpp (GGUF) 模型以及多種雲端 LLM 服務。透過多個 AI 審查委員的獨立審查、交叉辯論與最終裁決，為您的論文提供全方位的學術反饋。

## 🚀 核心新功能：雲端 LLM 支援

現已全面支援雲端 API，讓您在沒有高效能顯示卡的環境下也能流暢進行審查：

- **OpenAI 格式支援**：可對接 OpenAI (GPT-4o)、DeepSeek、Groq、OpenRouter 等所有相容 OpenAI 協定的 API。
- **Google Gemini 整合**：原生支援 Google Gemini API (如 `gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-2.0-flash-exp`)。
- **Gemini 模型偵測**：新增「🔍 偵測可用模型」功能，可自動查詢您的 API Key 權限下所有可用的 Gemini 模型名稱，解決 404 找不到模型的問題。

## ⚙️ 如何配置雲端模型

1. 啟動程式後，點擊側邊欄的 **⚙️ 參數設定**。
2. 在 **☁️ 雲端 LLM 設定** 區域中：
   - **API 類型**：選擇 `OpenAI-Compatible` 或 `Gemini`。
   - **模型來源預設**：若為 OpenAI 類型，可從下拉選單快速填入常見服務商 (如 DeepSeek) 的端點。
   - **API Key**：填入您的金鑰。
   - **模型名稱**：填入欲使用的模型識別碼 (如 `gpt-4o` 或 `gemini-1.5-flash`)。
3. 點擊 **💾 儲存並套用設定**。
4. 在側邊欄的 **🤖 LLM 快速切換** 中選擇 **☁️ 雲端 API** 即可開始使用。

## 📦 本地模型下載與安裝 (Model Installation)

由於本地模型檔案較大，請自行從以下連結下載並放入 `local_models/` 資料夾：

- **Gemma-3-TAIDE-12b (Q4_K_M)**: [下載連結](https://huggingface.co/taide/Gemma-3-TAIDE-12b-Chat-GGUF)
- **Meta-Llama-3-8B (Q4_K_M)**: [下載連結](https://huggingface.co/lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF)

下載後，請依照以下路徑存放：
`local_models/Gemma-3-TAIDE-12b-Chat-Q4_K_M.gguf`
`local_models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf`

## 💻 本地模型說明 (GGUF)

系統依然保留強大的本地隱私推論能力：

- **內建模型**：支援 Gemma-3 與 Llama-3 等 GGUF 格式模型。
- **自定義路徑**：您可點擊路徑旁的 **📂** 按鈕選取您硬碟中任何 `.gguf` 檔案。
- **上下文設定**：可自由調整 `n_ctx` (上下文窗口) 與 `max_tokens` (輸出上限)。

## 📁 檔案結構說明

- `PaperReviewSystem.exe`: 程式主執行檔。
- `config.json`: 儲存所有 API 金鑰、模型路徑與參數設定。
- `llm/interface.py`: 多供應商 LLM 調度核心。
- `app.py`: Streamlit 使用者介面。
- `_internal/local_models/`: 預設本地模型存放區。

## ⚠️ 注意事項

- **雲端 API 限制**：雲端模式需要穩定的網路連線，且需注意您的 API Token 消耗與 Rate Limit (TPM/RPM)。
- **Gemini 錯誤排除**：若使用 Gemini 出現 404 錯誤，請務必點擊「偵測可用模型」按鈕確認該 API Key 在您的區域支援的確切模型名稱。
- **隱私聲明**：本地模式 (`local`) 完全在您的電腦執行，論文內容不會外流；雲端模式 (`cloud`) 則會將內容傳送至對應的服務供應商 (如 OpenAI/Google)。

---
*本系統持續更新中，如有任何問題請參考各家 API 供應商之官方文檔。*
