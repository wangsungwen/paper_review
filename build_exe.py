# build_exe.py
import PyInstaller.__main__
import os
import sys
import shutil

# 取得必要套件的路徑，支援直接從 .venv 獲取 (不需 import)
def get_package_path(name):
    # 優先嘗試 import
    try:
        import importlib
        module = importlib.import_module(name)
        return os.path.dirname(module.__file__)
    except ImportError:
        # 如果 import 失敗，檢查 .venv 內的 site-packages
        venv_path = os.path.join(os.getcwd(), ".venv", "Lib", "site-packages", name)
        if os.path.exists(venv_path):
            return venv_path
        # 嘗試小寫/連字號轉換 (針對 llama-cpp-python)
        if name == "llama_cpp":
            alt_path = os.path.join(os.getcwd(), ".venv", "Lib", "site-packages", "llama_cpp")
            if os.path.exists(alt_path):
                return alt_path
        print(f"警告：找不到套件 {name} 的路徑。")
        return None

streamlit_pkg_path = get_package_path("streamlit")
llama_cpp_pkg_path = get_package_path("llama_cpp")
diskcache_pkg_path = get_package_path("diskcache")
tkinter_pkg_path = get_package_path("tkinter") or os.path.join(os.path.dirname(os.path.abspath(os.__file__)), "tkinter")
pypdf_pkg_path = get_package_path("pypdf")

from PyInstaller.utils.hooks import copy_metadata

# 包含元數據，防止 PackageNotFoundError
streamlit_metadata = copy_metadata('streamlit')
diskcache_metadata = copy_metadata('diskcache')

# 定義要包含的資料與資料夾
datas = [
    (streamlit_pkg_path, "streamlit") if streamlit_pkg_path else None,
    (llama_cpp_pkg_path, "llama_cpp") if llama_cpp_pkg_path else None,
    (diskcache_pkg_path, "diskcache") if diskcache_pkg_path else None,
    (tkinter_pkg_path, "tkinter") if tkinter_pkg_path else None,
    (pypdf_pkg_path, "pypdf") if pypdf_pkg_path else None,
    ("app.py", "."),
    ("config.json", "."),
    ("core", "core"),
    ("llm", "llm"),
    ("models", "models"),
    ("local_models", "local_models"),
]
datas = [d for d in datas if d is not None] + streamlit_metadata + diskcache_metadata

# 轉換為 PyInstaller 格式
data_args = []
for src, dst in datas:
    data_args.append(f"--add-data={src}{os.pathsep}{dst}")

# 執行 PyInstaller
PyInstaller.__main__.run([
    'run_app.py',                # 入口點
    '--name=PaperReviewSystem',  # 執行檔名稱
    '--onedir',                  # 產生目錄格式 (方便查看整合的檔案)
    '--noconsole',               # 不顯示控制台視窗 (Streamlit 會在瀏覽器開啟)
    '--additional-hooks-dir=.',  # 指定當前目錄為 Hook 路徑，以便載入 hook-streamlit.py
    *data_args,                  # 包含的資料
    '--hidden-import=streamlit',
    '--hidden-import=pandas',
    '--hidden-import=numpy',
    '--hidden-import=llama_cpp',
    '--hidden-import=diskcache',
    '--hidden-import=tkinter',
    '--hidden-import=_tkinter',
    '--hidden-import=pypdf',
    '--hidden-import=docx',
    '--hidden-import=lxml',
    '--clean',
    '--noconfirm',
])

print("\n打包完成！請開發 'dist/PaperReviewSystem' 資料夾查看結果。")
