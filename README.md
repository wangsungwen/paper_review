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
