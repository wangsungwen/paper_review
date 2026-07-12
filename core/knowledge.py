# core/knowledge.py
"""外部知識檢索模組 (RAG)。

提供三種「知識截斷」解決策略的底層實作：
1. fetch_arxiv     — Arxiv 最新論文摘要 (標準 XML 解析，非 regex)
2. fetch_web       — 聯網搜尋：優先 Tavily API，無金鑰時 fallback 至 Wikipedia
3. select_relevant_chunks — 以 TF-IDF 從上傳文獻中挑出與論文最相關的段落
"""

import re
import urllib.parse
import xml.etree.ElementTree as ET

import requests

ATOM_NS = "{http://www.w3.org/2005/Atom}"


# ==========================================
# 策略一：Arxiv 學術庫檢索
# ==========================================
def fetch_arxiv(query: str, max_results: int = 3, timeout: int = 8) -> str:
    """抓取 Arxiv 該領域最新發表的論文摘要，回傳整理後的文字。"""
    try:
        safe_query = urllib.parse.quote(query)
        url = (
            "https://export.arxiv.org/api/query"
            f"?search_query=all:{safe_query}&max_results={max_results}"
            "&sortBy=submittedDate&sortOrder=descending"
        )
        res = requests.get(url, timeout=timeout)
        res.raise_for_status()
        return parse_arxiv_feed(res.text)
    except Exception as e:
        return f"Arxiv 檢索失敗 ({e})"


def parse_arxiv_feed(xml_text: str, summary_limit: int = 400) -> str:
    """以標準 XML 解析 Arxiv Atom feed (取代脆弱的 regex 解析)。"""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        return f"Arxiv 回應格式錯誤 ({e})"

    lines = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        title_el = entry.find(f"{ATOM_NS}title")
        summary_el = entry.find(f"{ATOM_NS}summary")
        published_el = entry.find(f"{ATOM_NS}published")
        if title_el is None or summary_el is None:
            continue
        title = " ".join((title_el.text or "").split())
        summary = " ".join((summary_el.text or "").split())[:summary_limit]
        published = (published_el.text or "")[:10] if published_el is not None else ""
        lines.append(f"- 最新文獻 ({published}): {title}\n  摘要: {summary}...")

    return "\n".join(lines) if lines else "無相關最新文獻。"


# ==========================================
# 策略二：聯網搜尋 (Tavily 優先，Wikipedia fallback)
# ==========================================
def fetch_web(query: str, tavily_api_key: str = "", provider: str = "auto",
              timeout: int = 8) -> str:
    """搜尋領域最新網路資訊。

    provider: "auto" | "tavily" | "wikipedia"
    有設定 Tavily 金鑰時使用真正的網頁搜尋，否則退回 Wikipedia API。
    """
    use_tavily = tavily_api_key and provider in ("auto", "tavily")
    if use_tavily:
        result = _fetch_tavily(query, tavily_api_key, timeout)
        if not result.startswith("網頁檢索失敗"):
            return result
        # Tavily 失敗時自動退回 Wikipedia
    return _fetch_wikipedia(query, timeout)


def _fetch_tavily(query: str, api_key: str, timeout: int) -> str:
    try:
        res = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": 3,
                "include_answer": True,
            },
            timeout=timeout,
        )
        res.raise_for_status()
        data = res.json()
        lines = []
        if data.get("answer"):
            lines.append(f"- 綜合摘要: {data['answer']}")
        for item in data.get("results", [])[:3]:
            snippet = (item.get("content") or "")[:300]
            lines.append(f"- {item.get('title', '')}: {snippet}...")
        return "\n".join(lines) if lines else "無相關網頁資訊。"
    except Exception as e:
        return f"網頁檢索失敗 ({e})"


def _fetch_wikipedia(query: str, timeout: int) -> str:
    try:
        safe_query = urllib.parse.quote(query)
        url = (
            "https://zh.wikipedia.org/w/api.php"
            f"?action=query&list=search&srsearch={safe_query}&utf8=&format=json"
        )
        res = requests.get(url, timeout=timeout)
        res.raise_for_status()
        data = res.json()
        lines = []
        for item in data.get("query", {}).get("search", [])[:2]:
            snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
            lines.append(f"- {item.get('title')}: {snippet}...")
        return "\n".join(lines) if lines else "無相關網頁資訊。"
    except Exception as e:
        return f"網頁檢索失敗 ({e})"


# ==========================================
# 策略三：上傳文獻的相關段落檢索 (TF-IDF)
# ==========================================
def split_into_chunks(text: str, chunk_size: int = 1500, overlap: int = 200) -> list:
    """將長文本切成互相重疊的段落塊。"""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    step = max(chunk_size - overlap, 1)
    for start in range(0, len(text), step):
        chunk = text[start:start + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
        if start + chunk_size >= len(text):
            break
    return chunks


def select_relevant_chunks(reference_text: str, query: str,
                           max_chars: int = 12000, chunk_size: int = 1500) -> str:
    """從上傳的參考文獻中，挑出與論文主題最相關的段落 (總量不超過 max_chars)。

    優先使用 scikit-learn TF-IDF 餘弦相似度；未安裝時退回簡易關鍵詞比對。
    整份文獻已在預算內時直接全文回傳。
    """
    reference_text = (reference_text or "").strip()
    if not reference_text:
        return ""
    if len(reference_text) <= max_chars:
        return reference_text

    chunks = split_into_chunks(reference_text, chunk_size=chunk_size)
    if not chunks:
        return ""

    try:
        scores = _tfidf_scores(chunks, query)
    except Exception:
        scores = _keyword_scores(chunks, query)

    ranked = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)
    selected, total = [], 0
    for idx in ranked:
        if total + len(chunks[idx]) > max_chars:
            continue
        selected.append(idx)
        total += len(chunks[idx])
        if total >= max_chars * 0.95:
            break

    # 依原文順序輸出，保持可讀性
    selected.sort()
    return "\n...\n".join(chunks[i] for i in selected)


def _tfidf_scores(chunks: list, query: str) -> list:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    # analyzer="char_wb" 讓中文不需斷詞也能比對
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), max_features=20000)
    matrix = vectorizer.fit_transform(chunks + [query or ""])
    sims = cosine_similarity(matrix[-1], matrix[:-1])
    return sims[0].tolist()


def _keyword_scores(chunks: list, query: str) -> list:
    terms = [t.lower() for t in re.split(r"\W+", query or "") if len(t) >= 2]
    scores = []
    for chunk in chunks:
        low = chunk.lower()
        scores.append(sum(low.count(t) for t in terms))
    return scores
