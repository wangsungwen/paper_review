# models/paper.py

class Paper:
    def __init__(self, title: str, field: str, content: str, references: str = ""):
        self.title = title
        self.field = field
        self.content = content
        # 新增屬性：用於存放使用者動態上傳的最新參考文獻 (策略三)
        self.references = references