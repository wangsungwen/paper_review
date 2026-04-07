# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\wangs\\paper_review_system\\build_env\\Lib\\site-packages\\streamlit', 'streamlit'), ('C:\\Users\\wangs\\paper_review_system\\build_env\\Lib\\site-packages\\llama_cpp', 'llama_cpp'), ('C:\\Users\\wangs\\paper_review_system\\build_env\\Lib\\site-packages\\diskcache', 'diskcache'), ('C:\\Program Files\\Python311\\Lib\\tkinter', 'tkinter'), ('C:\\Users\\wangs\\paper_review_system\\build_env\\Lib\\site-packages\\pypdf', 'pypdf'), ('app.py', '.'), ('config.json', '.'), ('core', 'core'), ('llm', 'llm'), ('models', 'models'), ('local_models', 'local_models'), ('C:\\Users\\wangs\\paper_review_system\\build_env\\Lib\\site-packages\\streamlit-1.56.0.dist-info', 'streamlit-1.56.0.dist-info'), ('C:\\Users\\wangs\\paper_review_system\\build_env\\Lib\\site-packages\\diskcache-5.6.3.dist-info', 'diskcache-5.6.3.dist-info')],
    hiddenimports=['streamlit', 'pandas', 'numpy', 'llama_cpp', 'diskcache', 'tkinter', '_tkinter', 'pypdf', 'docx', 'lxml'],
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PaperReviewSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PaperReviewSystem',
)
