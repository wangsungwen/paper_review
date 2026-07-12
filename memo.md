請檢視這個專案開發架構及運作方案可否再優化升級

Ran 5 commands, read a file
檢視完成。整體架構（app / core / llm / models 分層 + 多輪審查編排）方向正確，但有幾個必須立即處理的問題和多個可升級點：

🚨 緊急：安全問題（請立刻處理）
config.json 內含真實的 Gemini API Key，且已被 git 追蹤並推上 GitHub（git ls-files 確認 config.json 在版控中，commit 5e1b5fd 訊息甚至寫明 "update cloud API key"）。.gitignore 雖有列 config.json，但檔案在加入 ignore 前就已被追蹤，所以無效。

必做三步：

立刻到 Google AI Studio 撤銷該金鑰並換新
git rm --cached config.json，改用 config.example.json（空值範本）入版控
用 git filter-repo 清除歷史中的金鑰
⚠️ 重大：Repo 肥大（.git 高達 11GB）
build/ 和 dist/ 整包（含 .exe、DLL、PYZ）被 commit 進 git。同樣是「先追蹤、後 ignore」的問題。建議 git rm -r --cached build dist 並用 filter-repo 清歷史，repo 可從 11GB 縮到幾 MB。

架構優化建議
版本管理：app_v1~v4.py、*_v1.py 等舊版複本應刪除——這正是 git 的工作，留著只會混淆維護。4 個 build 腳本 + 4 個 .spec 也應收斂成一個。

app.py 拆分（1204 行單體）：UI、config 管理、下載邏輯、審查流程全混在一起。建議拆成 ui/（頁面元件）、services/（config、模型下載）、保留 core/ 純邏輯，方便測試。

審查品質——最值得升級的一點：orchestrator.py 中論文內文被硬截斷為 content[:5000]，審查委員實際上只看到論文前幾頁。建議改為：分段摘要（map-reduce）後全文審查，或依模型 n_ctx 動態計算可用長度。

RAG 強化：Arxiv 用 regex 解析 XML（脆弱，建議改 feedparser 或 arxiv 套件）；「Web Search」實際只查 Wikipedia，名實不符，可接 Tavily/Serper 等真正搜尋 API。上傳文獻可進一步做 embedding 檢索（僅注入相關段落）取代整段前 15000 字硬塞。

其他：llm/interface.py 有 _has_blackwell = False 的 FIXME 硬編碼覆寫，偵測邏輯形同虛設；requirements.txt 是 UTF-16 編碼（PowerShell 重導向產生），Linux 上 pip 會解析失敗，應轉存 UTF-8；4 份 requirements 變體建議改用 pyproject.toml + extras（如 [gpu]）；測試僅一支，core 邏輯已與 UI 分離，很適合補 pytest。

要我直接動手嗎？我可以先做安全清理（移除金鑰與 build/dist 追蹤、產生 config.example.json、修 requirements 編碼），這部分風險最高也最急。金鑰撤銷需要你自己到 Google AI Studio 操作。

以上所有建議都可以一併動手清理、專案優化與升級

Ran 11 commands, updated tasks, loaded tools
The index is stable now (the earlier corruption came from the interrupted first git rm). Now writing the sanitized config files:

Created 3 files, read a file
⚠️ 重要：config.json 裡的 Gemini 金鑰（AIzaSy...Zs-yb0）已推上 GitHub 公開 repo，我無法替你撤銷。請立刻到 Google AI Studio 刪除該金鑰並建立新的。新金鑰之後填回本機 config.json（已不再入版控）或設環境變數 PRS_CLOUD_API_KEY 即可。

Ran 9 commands, read 5 files, updated tasks
Now reading the remaining small files before refactoring:

Ran a command
Now the code upgrades. First the new knowledge module (Task 6):

Created a file
Now the upgraded orchestrator (Tasks 5+6):

Created 2 files, updated tasks, read a file
Now adding the token-budget method and cleaning the stray import time:

Edited 2 files, updated tasks
Now the services layer (Task 4):

Created 4 files, edited 2 files
Edit 2 — remove the now-service-owned utility functions and config bootstrap:

Edited a file
Edit 3 — sidebar Ollama blocks now use the service:

Edited 2 files
Edit 4 — admin Ollama auto-install block:

Edited a file
Edit 5 — fix the markdown-mangled URLs in the admin settings:

Edited 4 files, ran 2 commands
The mount zero-padded the shrunk file. Stripping trailing NULs from all edited files:

Ran 4 commands
The mount truncated the orchestrator write. Rewriting via shell (which has proven reliable):

Ran 2 commands
llm/interface.py was also truncated by the sync layer. Repairing its tail:

Ran 2 commands
All modules compile now. Fixing build_exe.py (it was packaging config.json — with the key — into the EXE) and adding the services dir:

Updated tasks, edited a file, ran a command
Now the test suite (Task 9):

Created 4 files, ran a command
All 24 tests pass. Updating the README to match the new architecture:

Edited a file, ran a command
Everything verified. Committing the upgrade and installing the new .git into the project folder:

Ran 9 commands
The old-history backup folder is sync-locked from the VM side — it's gitignored and harmless; the user can delete it in Explorer. Final verification pass:

Ran 5 commands
The last two commits lived in the ghosted mounted .git — recommitting them onto the safe repo and regenerating the bundle:

Ran 5 commands
.git is now stable in the project folder with the remote configured. One last touch — ignore the bundle backup file, then wrap up:

Updated tasks, ran a command, read a file
全部完成，24 個單元測試全數通過，所有模組編譯無誤。摘要如下：

安全：金鑰已從 config.json 清空且該檔不再入版控（範本為 config.example.json）；EXE 打包不再內含設定檔；金鑰可改用環境變數 PRS_CLOUD_API_KEY 等注入。

Repo：.git 從 11GB 縮到不足 1MB（重建輕量 repo，4 個乾淨 commit）；build/dist/舊版複本全數移出版控；另存了一份 paper_review_repo.bundle 作為 repo 備份。

架構：app.py 瘦身 30%，抽出 services/（config、檔案、Ollama）；審查引擎移除 5000 字硬截斷，改為依模型 context 動態配置＋長文 map-reduce 摘要；RAG 升級為標準 XML 解析、Tavily 搜尋（管理介面可填 Key，無 Key 退回 Wikipedia）、TF-IDF 文獻節選；Blackwell 防閃退改由 config 控制；requirements 轉 UTF-8 並新增 pyproject.toml；新增 tests/ 共 24 個測試。

還需要你手動做三件事：

立刻撤銷舊 Gemini 金鑰（已公開在 GitHub）：到 Google AI Studio 刪除並換新，填回本機 config.json。
強制推送覆蓋 GitHub 上含金鑰的舊歷史：git push --force origin main（會取代遠端全部歷史，請確認沒有其他人依賴舊 repo）。
專案內的 .git_backup_pre_cleanup 資料夾是舊的 11GB git 歷史備份，確認新 repo 正常後可在檔案總管手動刪除。

D:\paper_review_system_multi\README.md
Document

D:\paper_review_system_multi\core\orchestrator.py

D:\paper_review_system_multi\core\knowledge.py

D:\paper_review_system_multi\config.example.json
Code
