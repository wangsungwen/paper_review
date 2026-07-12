# core/orchestrator.py

import asyncio
import json
import re

from core import knowledge

# 估算：中英混排下 1 token 約對應 2~3 字元，取保守值
CHARS_PER_TOKEN = 2.5


class PaperReviewOrchestrator:
    def __init__(self, paper, reviewers, llm, knowledge_config=None):
        self.paper = paper
        self.reviewers = reviewers
        self.llm = llm

        # 接收來自設定檔的「知識更新策略」開關
        self.knowledge_config = knowledge_config or {}

        # 在物件建立的瞬間立刻初始化這些屬性，
        # 就算後續模型斷線或降級，app.py 也抓得到預設值，不會報錯
        self.history = {"round_1": {}, "round_2": {}, "round_3": {}}
        self.review_stats = {
            "avg_contribution": 0.0,
            "avg_deficiencies": 0.0,
            "avg_robustness": 0.0,
        }

        # 論文內文的動態字元預算 (取代舊版 content[:5000] 硬截斷)
        self.paper_char_budget = self._compute_paper_budget()
        self._prepared_paper_text = None

    # ==========================================
    # 動態 Context 預算
    # ==========================================
    def _compute_paper_budget(self) -> int:
        """依據 LLM 引擎的 context window 動態計算論文可用的字元數。"""
        input_tokens = 8192  # 預設保守值
        getter = getattr(self.llm, "get_input_token_budget", None)
        if callable(getter):
            try:
                input_tokens = int(getter())
            except Exception:
                pass
        # 保留約 35% 空間給 system prompt、外部知識與模型輸出
        budget = int(input_tokens * CHARS_PER_TOKEN * 0.65)
        return max(4000, min(budget, 120000))

    async def _prepare_paper_text(self) -> str:
        """回傳注入 Prompt 的論文內文。

        - 長度在預算內 → 直接用全文 (舊版永遠只取前 5000 字，長論文的
          方法與實驗章節根本沒被審到)。
        - 超過預算 → map-reduce：分段請 LLM 摘要，再與開頭原文合併。
        """
        if self._prepared_paper_text is not None:
            return self._prepared_paper_text

        content = self.paper.content or ""
        if len(content) <= self.paper_char_budget:
            self._prepared_paper_text = content
            return content

        # ---- map：各段並行摘要 ----
        chunk_size = max(int(self.paper_char_budget * 0.8), 3000)
        chunks = knowledge.split_into_chunks(content, chunk_size=chunk_size, overlap=200)

        async def summarize(idx, chunk):
            sys_p = (
                "You are an expert academic summarizer. Summarize the following "
                "section of a research paper in about 300-500 words, preserving "
                "key methods, data, results and claims. Reply in the paper's language."
            )
            return await self.llm.generate_response(
                sys_p, f"[Section {idx + 1}/{len(chunks)}]\n{chunk}"
            )

        summaries = await asyncio.gather(
            *[summarize(i, c) for i, c in enumerate(chunks)]
        )

        # ---- reduce：開頭保留原文 (摘要/導論)，其餘用摘要 ----
        head_len = int(self.paper_char_budget * 0.4)
        head = content[:head_len]
        digest = "\n\n".join(
            f"[第 {i + 1} 段摘要]\n{s}" for i, s in enumerate(summaries)
        )
        prepared = (
            f"{head}\n\n"
            f"--- 以下為論文其餘部分之逐段摘要 (原文過長，已自動壓縮) ---\n\n"
            f"{digest}"
        )
        self._prepared_paper_text = prepared[: self.paper_char_budget + head_len]
        return self._prepared_paper_text

    # ==========================================
    # 匯整外部知識 (知識截斷解決方案)
    # ==========================================
    async def _gather_external_knowledge(self):
        knowledge_blocks = []

        # 策略一：Arxiv 學術庫
        if self.knowledge_config.get("enable_rag") and self.paper.field:
            rag_text = await asyncio.to_thread(knowledge.fetch_arxiv, self.paper.field)
            if rag_text and "無相關" not in rag_text and "失敗" not in rag_text:
                knowledge_blocks.append(
                    f"【學術資料庫檢索結果 (Arxiv 最新發表)】\n{rag_text}"
                )

        # 策略二：聯網搜尋 (Tavily 優先，無金鑰 fallback Wikipedia)
        if self.knowledge_config.get("enable_web_search") and self.paper.field:
            web_text = await asyncio.to_thread(
                knowledge.fetch_web,
                self.paper.field,
                self.knowledge_config.get("tavily_api_key", ""),
                self.knowledge_config.get("web_search_provider", "auto"),
            )
            if web_text and "無相關" not in web_text and "失敗" not in web_text:
                knowledge_blocks.append(f"【聯網搜尋最新趨勢 (Web Search)】\n{web_text}")

        # 策略三：使用者上傳文獻 → TF-IDF 挑出與論文最相關的段落
        # (取代舊版「前 15000 字硬塞」，長文獻的相關內容不再被截掉)
        if self.knowledge_config.get("enable_reference_upload") and getattr(
            self.paper, "references", ""
        ):
            query = f"{self.paper.title} {self.paper.field}"
            relevant = await asyncio.to_thread(
                knowledge.select_relevant_chunks,
                self.paper.references,
                query,
                12000,
            )
            if relevant:
                knowledge_blocks.append(
                    f"【使用者動態補充之最新參考文獻 (已自動節選相關段落)】\n{relevant}"
                )

        if knowledge_blocks:
            return "\n\n".join(knowledge_blocks)
        return ""

    # ==========================================
    # 三輪審查流程
    # ==========================================
    async def run_round_1(self):
        """第一輪：獨立審查"""
        # 並行準備：外部知識 + 論文內文 (長文自動 map-reduce 摘要)
        external_knowledge, prepared_content = await asyncio.gather(
            self._gather_external_knowledge(),
            self._prepare_paper_text(),
        )

        paper_text = f"Title: {self.paper.title}\nContent:\n{prepared_content}"

        tasks = []
        for reviewer in self.reviewers:
            system_prompt = (
                f"You are {reviewer.name}, an expert in {reviewer.expertise}. "
                f"Your style is: {reviewer.style}. "
                "Please review the following paper."
            )
            if external_knowledge:
                user_prompt = (
                    f"【系統提示：為了解決知識截斷問題，以下提供最新外部參考資訊，"
                    f"請務必將此最新資訊納入審查考量】\n"
                    f"{external_knowledge}\n\n"
                    f"【待審查論文】\n{paper_text}"
                )
            else:
                user_prompt = paper_text

            tasks.append(self.llm.generate_response(system_prompt, user_prompt))

        responses = await asyncio.gather(*tasks)
        for idx, reviewer in enumerate(self.reviewers):
            self.history["round_1"][reviewer.name] = responses[idx]

        return self.history["round_1"]

    async def run_round_2(self):
        """第二輪：交叉辯論"""
        tasks = []
        for reviewer in self.reviewers:
            other_reviews = "\n\n".join(
                [
                    f"{r.name}'s review:\n{self.history['round_1'][r.name]}"
                    for r in self.reviewers
                    if r != reviewer
                ]
            )

            system_prompt = (
                f"You are {reviewer.name}. Read the reviews of your colleagues and "
                f"provide your rebuttal or agreement. "
                f"Maintain your persona: {reviewer.expertise}, {reviewer.style}."
            )
            user_prompt = f"Colleague Reviews:\n{other_reviews}\n\nYour rebuttal:"
            tasks.append(self.llm.generate_response(system_prompt, user_prompt))

        responses = await asyncio.gather(*tasks)
        for idx, reviewer in enumerate(self.reviewers):
            self.history["round_2"][reviewer.name] = responses[idx]

        return self.history["round_2"]

    async def run_round_3(self):
        """第三輪：最終共識與評分 (強制要求 JSON)"""
        chair = self.reviewers[0]

        all_prior_context = (
            "Round 1:\n"
            + "\n".join([f"{k}: {v}" for k, v in self.history["round_1"].items()])
            + "\n\nRound 2:\n"
            + "\n".join([f"{k}: {v}" for k, v in self.history["round_2"].items()])
        )

        system_prompt = (
            f"You are {chair.name}, acting as the Area Chair. "
            "Synthesize the debate and output the final decision STRICTLY as a JSON object. "
            "Do not include Markdown blocks like ```json. Just output the raw JSON.\n\n"
            "Format:\n"
            "{\n"
            '  "summary": "String summarizing the final decision",\n'
            '  "avg_contribution": float (0.0 to 10.0),\n'
            '  "avg_deficiencies": float (0.0 to 10.0),\n'
            '  "avg_robustness": float (0.0 to 10.0)\n'
            "}"
        )
        user_prompt = f"Debate History:\n{all_prior_context}\n\nProvide the final JSON verdict:"

        response = await self.llm.generate_response(system_prompt, user_prompt)
        self.history["round_3"]["Final Verdict"] = response
        self.parse_final_verdict(response)
        return self.history["round_3"]

    def parse_final_verdict(self, response: str):
        """強健的 JSON 解析機制 (獨立方法，方便單元測試)。"""
        import json as _json
        import re as _re
        try:
            json_match = _re.search(r"\{.*\}", response, _re.DOTALL)
            json_str = json_match.group() if json_match else response

            parsed_data = _json.loads(json_str)

            self.review_stats["avg_contribution"] = float(
                parsed_data.get("avg_contribution", 0.0)
            )
            self.review_stats["avg_deficiencies"] = float(
                parsed_data.get("avg_deficiencies", 0.0)
            )
            self.review_stats["avg_robustness"] = float(
                parsed_data.get("avg_robustness", 0.0)
            )

            self.history["round_3"]["Final Verdict"] = parsed_data.get(
                "summary", "無法從 JSON 中提取 summary。"
            )
        except (_json.JSONDecodeError, ValueError, TypeError):
            self.history["round_3"]["Final Verdict"] = (
                f"⚠️ 模型未輸出標準 JSON 格式，無法解析評分。\n\n"
                f"**原始輸出內容：**\n{response}"
            )
