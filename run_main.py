import os
import sys
import streamlit.web.cli as stcli

if __name__ == "__main__":
    # 關鍵：判斷程式是否處於打包後的執行狀態
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # 如果是打包狀態，自動定位到系統背景解壓縮的暫存目錄讀取 app.py
        app_path = os.path.join(sys._MEIPASS, "app.py")
    else:
        # 如果是平常開發狀態，讀取當前目錄的 app.py
        app_path = "app.py"

    # 強制指定 Streamlit 執行包在裡面的 app.py
    sys.argv = ["streamlit", "run", app_path, "--global.developmentMode=false"]
    sys.exit(stcli.main())