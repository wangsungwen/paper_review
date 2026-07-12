# build_exe.py
import PyInstaller.__main__
import os

# 定義要包含的資料路徑
# 格式: (原始路徑, 打包後的相對路徑)
# 注意：config.json (含 API 金鑰) 絕不打包進執行檔！
# 執行檔啟動時會在 exe 旁自動生成無金鑰的預設 config.json。
assets = [
    ("app.py", "."),
    ("core", "core"),
    ("llm", "llm"),
    ("models", "models"),
    ("services", "services"),
]

# 組合 --add-data 參數
# Windows 下使用分號 ";" 分隔
data_args = []
for src, dst in assets:
    if os.path.exists(src):
        data_args.append(f"--add-data={src}{os.pathsep}{dst}")

# 隱藏匯入 (Streamlit 打包常需要的)
hidden_imports = [
    "streamlit",
    "pypdf",
    "docx",
    "torch",
    "transformers",
    "llama_cpp",
    "charset_normalizer",
    "sklearn.utils._cython_blas",
    "sklearn.neighbors.typedefs",
    "sklearn.neighbors.quad_tree",
    "sklearn.tree._utils",
]

# 執行打包
PyInstaller.__main__.run([
    "run_app.py",
    "--additional-hooks-dir=.",
    "--onedir",
    "--name=PaperReviewSystem",
    *data_args,
    "--collect-all=streamlit",
    "--collect-all=torch",
    "--collect-all=transformers",
    "--collect-all=pyarrow",
    "--collect-all=altair",
    "--collect-all=pypdf",
    "--collect-all=docx", # python-docx
    "--collect-all=requests",
    "--copy-metadata=streamlit", # 解決 PackageNotFoundError
    "--noconfirm", # 自動覆寫舊檔
    "--clean",
])
