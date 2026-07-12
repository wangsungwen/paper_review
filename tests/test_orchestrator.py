# tests/test_orchestrator.py
import asyncio

import pytest

from core.orchestrator import PaperReviewOrchestrator
from models.paper import Paper
from models.reviewer import ReviewerAgent


class MockLLM:
    """記錄呼叫並回傳固定內容的假 LLM。"""

    def __init__(self, response="mock review", input_tokens=8192):
        self.response = response
        self.input_tokens = input_tokens
        self.calls = []

    def get_input_token_budget(self):
        return self.input_tokens

    async def generate_response(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return self.response


def make_orchestrator(content="short paper", llm=None, **kw):
    paper = Paper(title="T", field="AI", content=content)
    reviewers = [
        ReviewerAgent("A", "CV", "nets", "strict"),
        ReviewerAgent("B", "Edge", "mcu", "practical"),
    ]
    return PaperReviewOrchestrator(paper, reviewers, llm or MockLLM(), **kw)


# ---------- 初始化防呆 ----------
def test_stats_initialized_before_any_round():
    orch = make_orchestrator()
    assert orch.review_stats["avg_contribution"] == 0.0
    assert orch.history["round_3"] == {}


# ---------- 動態 context 預算 ----------
def test_budget_scales_with_llm_context():
    small = make_orchestrator(llm=MockLLM(input_tokens=4096))
    large = make_orchestrator(llm=MockLLM(input_tokens=200000))
    assert small.paper_char_budget < large.paper_char_budget
    assert large.paper_char_budget <= 120000  # 上限保護


def test_budget_survives_llm_without_budget_api():
    class Bare:
        async def generate_response(self, s, u):
            return "x"

    orch = PaperReviewOrchestrator(
        Paper("T", "AI", "c"), [ReviewerAgent("A", "e", "f", "s")], Bare()
    )
    assert orch.paper_char_budget >= 4000


# ---------- 長文 map-reduce ----------
def test_short_paper_used_verbatim():
    llm = MockLLM()
    orch = make_orchestrator(content="short content", llm=llm)
    text = asyncio.run(orch._prepare_paper_text())
    assert text == "short content"
    assert llm.calls == []  # 不需摘要


def test_long_paper_triggers_map_reduce():
    llm = MockLLM(response="segment summary", input_tokens=4096)
    long_content = "詞" * 50000
    orch = make_orchestrator(content=long_content, llm=llm)
    text = asyncio.run(orch._prepare_paper_text())
    assert len(llm.calls) > 0  # 有呼叫 LLM 做分段摘要
    assert "segment summary" in text
    assert len(text) < len(long_content)  # 有被壓縮
    # 開頭原文保留
    assert text.startswith("詞")


# ---------- Round 1 注入內容 ----------
def test_round_1_uses_full_content_not_5000_cap():
    llm = MockLLM(input_tokens=200000)
    content = "x" * 20000  # 舊版會被截到 5000
    orch = make_orchestrator(content=content, llm=llm)
    asyncio.run(orch.run_round_1())
    # 兩位審查委員各一次呼叫
    assert len(llm.calls) == 2
    _, user_prompt = llm.calls[0]
    assert content in user_prompt


# ---------- 最終裁決 JSON 解析 ----------
def test_parse_valid_json():
    orch = make_orchestrator()
    orch.parse_final_verdict(
        '{"summary": "Accept", "avg_contribution": 8.5, '
        '"avg_deficiencies": 3.0, "avg_robustness": 7.0}'
    )
    assert orch.review_stats["avg_contribution"] == 8.5
    assert orch.history["round_3"]["Final Verdict"] == "Accept"


def test_parse_json_wrapped_in_markdown():
    orch = make_orchestrator()
    orch.parse_final_verdict(
        '```json\n{"summary": "Reject", "avg_contribution": 2.0, '
        '"avg_deficiencies": 9.0, "avg_robustness": 1.5}\n```'
    )
    assert orch.review_stats["avg_deficiencies"] == 9.0
    assert orch.history["round_3"]["Final Verdict"] == "Reject"


def test_parse_invalid_json_keeps_zero_and_raw_output():
    orch = make_orchestrator()
    orch.parse_final_verdict("I refuse to output JSON")
    assert orch.review_stats["avg_contribution"] == 0.0
    assert "I refuse to output JSON" in orch.history["round_3"]["Final Verdict"]


def test_parse_json_missing_fields_defaults_zero():
    orch = make_orchestrator()
    orch.parse_final_verdict('{"summary": "Weak accept"}')
    assert orch.review_stats["avg_robustness"] == 0.0
    assert orch.history["round_3"]["Final Verdict"] == "Weak accept"
