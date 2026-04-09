# 多代理人論文審查系統 - 使用說明 (v4.0)

本系統是一個基於 Streamlit 的多代理人 AI 論文審查平台，專為高階硬體 (如 NVIDIA RTX 5090) 優化。支援本地 Ollama、Llama-cpp (GGUF) 以及多種雲端 LLM 服務，提供深度學術審查與 AI 寫作偵測。

---

## 🌟 核心功能說明 (v4.0 更新)

### 1. 🔍 進化版 AI 寫作偵測

系統整合了最前線的 AI 寫作識別技術，支援三種強大運行模式：

- **Hugging Face 神經網路精準推論 (推薦)**：使用 `desklib/ai-text-detector-v1.01`。
  - **Blackwell 硬體相容性**：針對 RTX 50 系列提供 `force_cpu` 模式，避免 CUDA 核心不相容錯誤，同時保持極速。
- **本地 LLM 語義分析**：利用本地語言模型分析文本風格、連貫性與語義特徵進行判定。
- **雲端模式 (GPTZero)**：對接 GPTZero API，提供第三方的機率基準。

### 2. 🤖 本地 LLM 多引擎驅動

- **🐑 Ollama API (強烈推薦)**：原生支援 Ollama，提供 Windows 上最穩定的本地顯卡加速體驗，支援 Llama 3.1、DeepSeek 等熱門模型。
- **💻 Llama-cpp (GGUF)**：支援手動載入 GGUF 模型，並具備全顯存卸載 (`n_gpu_layers=-1`) 優化。
- **⚙️ 靈活切換**：側邊欄提供一鍵切換功能，並可手動觸發 **「🔍 檢測推論硬體狀態」** 以節省初始化資源。

### 3. 🚀 多代理人學術審查

- **多輪對話機制**：獨立審查 -> 交叉辯論 -> 最終裁決，挖掘論文深層問題。
- **自定義委員**：可隨時新增具有特定學術背景的審查委員。

### 4. 📄 跨格式讀取與持久化報告

- 支援 `.pdf`、`.docx` 及 `.txt`。
- 支援匯出為 **JSON** 或 **Markdown** 格式。
- 報表結果持久化，切換頁面不遺失。

---

## ⚙️ 系統設定指引

1. **安裝環境**：
   - 建議版本：**Python 3.11** 或 **3.12**。
   - 核心依賴：使用命令列安裝對應顯卡版本的 PyTorch。

2. **本地模型配置**：
   - **Ollama**：下載後執行 `ollama pull llama3.1` 即可直接使用。
   - **Llama-cpp**：將 `.gguf` 放入 `local_models/` 後在界面選取。

3. **顯卡優化**：
   - 針對 RTX 5090 用戶，請參考內附的 `gpu_setup_guide.md` 進行進階配置。

---

## 📦 快速安裝備忘

```powershell
# 1. 建立並啟動環境
python -m venv .venv
.\.venv\Scripts\activate

# 2. 安裝 CUDA 版 Torch (範例：cu124)
pip install torch--extra-index-url https://download.pytorch.org/whl/cu124

# 3. 安裝其餘套件
pip install -r requirements.txt
```

---

## ⚠️ 常見問題

- **CUDA Error**：若看到 `no kernel image`，請在 `config.json` 開啟 `"force_cpu": true` 或安裝 PyTorch Nightly。
- **Ollama 不可用**：請檢查 Ollama 應用程式是否已啟動且正在運行中。

---
*本系統由 AI 協作開發，旨在提升學術論文的審查效率與品質。*
