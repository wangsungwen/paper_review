# hook-streamlit.py
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

datas = copy_metadata('streamlit') + collect_data_files('streamlit')
