# run_app.py
import streamlit.web.cli as stcli
import os, sys

def resolve_path(path):
    """取得相對於執行路徑的絕對路徑"""
    if getattr(sys, 'frozen', False):
        # 執行檔環境
        resolved_path = sys._MEIPASS
    else:
        # 開發環境
        resolved_path = os.path.abspath(os.getcwd())
    return os.path.join(resolved_path, path)

if __name__ == "__main__":
    # 強制將目前的目錄加入路徑，確保模組 import 正常
    current_dir = os.path.abspath(os.getcwd())
    if current_dir not in sys.path:
        sys.path.append(current_dir)

    # Streamlit 啟動參數
    # 我們將 app.py 打包在執行檔內部，或放在執行檔旁邊
    # 這裡假設 app.py 在 sys._MEIPASS 中 (如果是單一檔案打包)
    app_path = resolve_path("app.py")
    
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())
