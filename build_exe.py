# build_exe.py
import PyInstaller.__main__
import os
import streamlit
import llama_cpp
import diskcache
import tkinter
import pypdf
import shutil

# 取得必要套件的絕對路徑，以便 PyInstaller 正確打包
streamlit_pkg_path = os.path.dirname(streamlit.__file__)
llama_cpp_pkg_path = os.path.dirname(llama_cpp.__file__)
diskcache_pkg_path = os.path.dirname(diskcache.__file__)
tkinter_pkg_path = os.path.dirname(tkinter.__file__)
pypdf_pkg_path = os.path.dirname(pypdf.__file__)

from PyInstaller.utils.hooks import copy_metadata

# 取得 Streamlit 的路徑，以便包含必要的靜態資源
streamlit_pkg_path = os.path.dirname(streamlit.__file__)

# 包含元數據，防止 PackageNotFoundError
streamlit_metadata = copy_metadata('streamlit')
diskcache_metadata = copy_metadata('diskcache')

# 定義要包含的資料與資料夾
datas = [
    (streamlit_pkg_path, "streamlit"),
    (llama_cpp_pkg_path, "llama_cpp"),
    (diskcache_pkg_path, "diskcache"),
    (tkinter_pkg_path, "tkinter"),
    (pypdf_pkg_path, "pypdf"),
    ("app.py", "."),
    ("config.json", "."),
    ("core", "core"),
    ("llm", "llm"),
    ("models", "models"),
    ("local_models", "local_models"),
] + streamlit_metadata + diskcache_metadata

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
