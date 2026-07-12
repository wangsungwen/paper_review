# tests/test_knowledge.py
from core import knowledge

SAMPLE_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>YOLOv12: Attention-Centric Real-Time Object Detectors</title>
    <summary>We propose an attention-centric framework
    that improves accuracy while keeping latency low.</summary>
    <published>2026-01-15T00:00:00Z</published>
  </entry>
  <entry>
    <title>Second Paper</title>
    <summary>Another abstract.</summary>
    <published>2026-01-10T00:00:00Z</published>
  </entry>
</feed>
"""


# ---------- Arxiv XML 解析 ----------
def test_parse_arxiv_feed_extracts_entries():
    result = knowledge.parse_arxiv_feed(SAMPLE_ATOM)
    assert "YOLOv12" in result
    assert "Second Paper" in result
    assert "2026-01-15" in result
    # 換行已清洗
    assert "attention-centric framework that improves" in result.replace("  ", " ")


def test_parse_arxiv_feed_handles_malformed_xml():
    result = knowledge.parse_arxiv_feed("<not-valid-xml")
    assert "格式錯誤" in result


def test_parse_arxiv_feed_empty_feed():
    empty = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
    assert "無相關" in knowledge.parse_arxiv_feed(empty)


# ---------- 分塊 ----------
def test_split_into_chunks_short_text():
    assert knowledge.split_into_chunks("hello") == ["hello"]


def test_split_into_chunks_covers_all_text():
    text = "a" * 5000
    chunks = knowledge.split_into_chunks(text, chunk_size=1500, overlap=200)
    assert all(len(c) <= 1500 for c in chunks)
    # 重組後涵蓋原文長度
    assert sum(len(c) for c in chunks) >= len(text)


# ---------- TF-IDF 相關段落節選 ----------
def test_select_relevant_chunks_returns_all_when_small():
    ref = "short reference text"
    assert knowledge.select_relevant_chunks(ref, "query", max_chars=1000) == ref


def test_select_relevant_chunks_prefers_related_content():
    related = "深度學習 物件偵測 YOLO 神經網路 卷積 " * 60      # ~1500 chars
    unrelated = "烹飪 食譜 甜點 烘焙 麵粉 奶油 巧克力 蛋糕 " * 60
    ref = unrelated + related + unrelated
    result = knowledge.select_relevant_chunks(
        ref, "YOLO 物件偵測 深度學習", max_chars=2000, chunk_size=1000
    )
    assert "YOLO" in result
    assert len(result) <= 2600  # 預算控制 (含連接符寬容值)


def test_select_relevant_chunks_empty_input():
    assert knowledge.select_relevant_chunks("", "q") == ""


# ---------- 關鍵詞 fallback ----------
def test_keyword_scores_ranks_matching_chunk_higher():
    chunks = ["nothing here", "yolo yolo detection", "cooking recipes"]
    scores = knowledge._keyword_scores(chunks, "yolo detection")
    assert scores[1] > scores[0]
    assert scores[1] > scores[2]
