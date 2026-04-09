# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=[],
    datas=[('app.py', '.'), ('config.json', '.'), ('core', 'core'), ('llm', 'llm'), ('models', 'models')],
    hiddenimports=['streamlit', 'pypdf', 'docx', 'torch', 'transformers', 'llama_cpp', 'charset_normalizer', 'sklearn.utils._cython_blas', 'sklearn.neighbors.typedefs', 'sklearn.neighbors.quad_tree', 'sklearn.tree._utils'],
    hookspath=[],
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
    console=True,
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
