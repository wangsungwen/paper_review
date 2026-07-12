# 多代理人論文審查系統 - 使用說明 (v5.5 終極知識聯網版)

本系統是一個專業級的多代理人 AI 論文審查平台，已全面升級為 **網頁伺服器架構**。特別針對高階硬體 (如 NVIDIA RTX 5090 Blackwell) 進行深度優化，支援大規模併發連線、會話隔離隱私保護與全域模型快取，並**全新導入動態知識擴充機制以突破 AI 知識時間落差**。

---

## 🌟 核心功能說明 (v5.5 伺服器版更新)

### 1. 🌐 多人伺服器架構 (Server-Ready)
- **記憶體隔離防護**：使用者的 API Key 與模型偏好完全儲存在瀏覽器會話 (`st.session_state`) 中。**隨改隨套用，且絕不會被寫入伺服器硬碟**，確保多人同時使用時金鑰不外洩。
- **全網域單例快取 (Global Singleton Cache)**：本地大型模型 (Llama GGUF, Ollama, HF) 採用「全域載入一次」機制，防止多人連線導致顯存/記憶體溢出 (OOM) 崩潰。

### 2. 📚 動態知識擴充 (突破 LLM 知識截斷) **[v5.5 全新主打]**
為解決本地模型與雲端 API 不認識最新技術名詞（例如：模型可能尚未學習到最新的 YOLOv12/v26 架構，或是未能掌握 Amodal Generative Augmentation 與 RGB-T 多模態融合等前沿研究技術）的時間落差痛點，系統內建三大檢索增強 (RAG) 策略，管理員可於參數設定內自由隨時選用單一或多個策略併行：
- **策略一、啟用學術庫連線**：自動爬取 Arxiv 領域最新發表的論文摘要，作為代理人的背景知識。
- **策略二、啟用代理人聯網搜尋**：透過 Web Search 自動搜尋領域最新百科與趨勢資訊。
- **策略三、啟用動態參考文獻上傳**：於主畫面「1.2」新增上傳區塊，讓使用者直接「手動補充/複選上傳」多篇最新參考文獻 (PDF/Docx/TXT)，系統會自動萃取文字並無縫注入審查委員的認知上下文中。

### 3. 🔍 進化版 AI 寫作偵測
- **Hugging Face 精準推論**：整合 `desklib/ai-text-detector-v1.01` 神經網路模型，提供逐句熱力圖分析。
- **Blackwell 硬體相容性**：內建 UI 切換開關，一鍵開啟 `force_cpu` 模式解決 50 系顯卡架構過新導致的 CUDA (`no kernel image`) 錯誤。

### 4. 🤖 本地 LLM 多引擎驅動
- **🐑 Ollama API (強烈推薦)**：提供極佳的連線穩定性。**[新功能]** 內建 Ollama 服務自動偵測機制；若尚未安裝，只需在設定介面一鍵點擊，系統即可在背景自動下載並安裝 Ollama，體驗開箱即用。
- **💻 Llama-cpp (GGUF)**：支援伺服器端管理員統一配置 GGUF 模型路徑與上下文窗口，支援 GPU 加速。
- **✨ 雲端 API 支援**：支援 OpenAI 格式 (DeepSeek, Groq 等) 以及 Google Gemini 原生 SDK (支援自訂模型名稱)。

### 5. 📄 跨格式讀取與持久化報告
- 支援 `.pdf`、`.docx` 及 `.txt`。
- 內建字數預處理功能，可自動排除「參考文獻、附錄」或手動指定排除字串，防止長文本 Token 溢出報錯。
- 支援匯出為 JSON 或 Markdown 與熱力圖分析。

---

## ⚙️ 系統設定與部署

### 1. 管理員靜態配置 (`config.json`)
管理員可透過專案目錄下的 `config.json` 預設伺服器端的本地模型路徑與知識更新策略的預設開關。一般使用者無權修改物理檔案路徑，確保伺服器穩定。

### 2. 跨平台部署與啟動

#### 【環境 A】Windows 原生部署
```powershell
# 1. 建立並啟動環境
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install blinker streamlit
python -m pip install pypdf python-docx
python -m pip install transformers pandas scikit-learn aiohttp sentencepiece tokenizers safetensors altair watchdog

# 2. 安裝 CUDA 版 Torch 與其他套件
pip install torch --extra-index-url [https://download.pytorch.org/whl/cu124](https://download.pytorch.org/whl/cu124)
pip install -r requirements.txt

# 3. 下載 Hugging Face 模型
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\download_model.ps1

# 4. 執行伺服器
streamlit run app.py
```

#### 【環境 B】Ubuntu / Linux 部署全手冊 (RTX 5090 終極相容版)
針對搭載 RTX 5090 且需完全發揮 GPU 滿血算力的 Linux 環境，請依序執行以下環境建置與優化編譯流程，以避開套件衝突：

```bash
# 1. 系統資源與環境準備
sudo apt update
sudo apt install -y python3-venv python3-full nvidia-cuda-toolkit build-essential cmake zstd

# 2. 建立並進入虛擬環境
cd ~/PaperReviewMultiSystem
python3 -m venv .venv
source .venv/bin/activate

# 3. 核心修正：解除 requirements.txt 的 PyTorch 封印 (防止 pip 崩潰)
cp requirements.txt requirements.txt.bak
sed -i -E '/^(torch|torchvision|torchaudio)(==|>=|<=|$)/Id' requirements.txt

# 4. 安裝相容的 PyTorch 2.6.0 (CUDA 12.4)
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124

# 5. 強制配置 RTX 5090 (sm_89 向下相容) 高效能編譯參數並安裝依賴
export CUDACXX=/usr/bin/nvcc
export CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=89"
export FORCE_CMAKE="1"
pip install --upgrade --force-reinstall llama-cpp-python --no-cache-dir
pip install -r requirements.txt

# 6. [選用] 本地化 GGUF 模型檔案下載 (Hugging Face)
hf auth login
mkdir -p local_models
hf download nctu6/Gemma-3-TAIDE-12b-Chat-GGUF Gemma-3-TAIDE-12b-Chat-Q4_K_M.gguf --local-dir ./local_models
hf download QuantFactory/Meta-Llama-3-8B-Instruct-GGUF Meta-Llama-3-8B-Instruct.Q4_K_M.gguf --local-dir ./local_models

# 7. 啟動伺服器
streamlit run app.py
```

#### 【環境 C】Docker 容器化無痛部署 (無干擾推薦)
如果您希望完全隔絕環境污染，可以直接使用 Docker 化架構一鍵啟動：

```bash
# 背景部署容器 (包含自動透通掛載 config 與 local_models)
docker compose up -d
```
若要在 Docker 內啟用 NVIDIA GPU 加速，請先取消 `docker-compose.yml` 內 deploy 區塊的註解。

### 3. 打包與發佈 (EXE 版)
如果您希望將此系統作為無須安裝環境的可攜式軟體分發：

```powershell
python build_exe.py
```
執行完後，結果將輸出於 `dist/PaperReviewSystem/` 內。 **注意**：為避免執行檔體積過大，`local_models` 模型資料夾與裡面的 `.gguf` 並未被打包。請務必在發布前，手動將 `local_models` 資料夾複製並放置於 `PaperReviewSystem.exe` 同一層級！

---

## ⚠️ 常見問題
- **隱私安全性**：畫面上輸入的所有 API 金鑰僅存在於您的瀏覽器視窗中，登出或重新整理即清除，後台管理員無法窺視。
- **驅動與 CUDA Error**：若遇到 `no kernel image`，請至「⚙️ 參數設定」勾選「強制使用 CPU 進行 AI 偵測」。若啟動時遇到 `cudaGetDriverEntryPointByVersion` 錯誤，請更新實體主機的 NVIDIA 顯示卡驅動。

---
*本系統旨在透過多代理人協作與動態知識擴充，全面提升學術論文的審查效率與品質。*