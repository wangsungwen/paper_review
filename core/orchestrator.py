# core/orchestrator.py

import asyncio
import json
import re
import requests
import urllib.parse

class PaperReviewOrchestrator:
    def __init__(self, paper, reviewers, llm, knowledge_config=None):
        self.paper = paper
        self.reviewers = reviewers
        self.llm = llm
        
        # 接收來自設定檔的「知識更新策略」開關
        self.knowledge_config = knowledge_config or {}
        
        # 【關鍵修復】：在物件建立的瞬間，立刻初始化這些屬性
        # 這樣就算後續模型斷線或降級，app.py 也絕對抓得到預設值 0.0，不會報錯！
        self.history = {"round_1": {}, "round_2": {}, "round_3": {}}
        self.review_stats = {
            "avg_contribution": 0.0,
            "avg_deficiencies": 0.0,
            "avg_robustness": 0.0
        }

    # ==========================================
    # 策略一：RAG (檢索增強生成) - 自動爬取 Arxiv 最新論文摘要
    # ==========================================
    def _fetch_arxiv(self, query):
        try:
            safe_query = urllib.parse.quote(query)
            # 搜尋該領域最新提交的 2 篇論文摘要
            url = f"http://export.arxiv.org/api/query?search_query=all:{safe_query}&max_results=2&sortBy=submittedDate&sortOrder=desc"
            res = requests.get(url, timeout=5)
            res.raise_for_status()
            
            entries = re.findall(r'<entry>(.*?)</entry>', res.text, re.DOTALL)
            result = ""
            for entry in entries:
                title = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                summary = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
                if title and summary:
                    # 清洗換行符號
                    clean_summary = summary.group(1).strip().replace('\n', ' ')
                    result += f"- 最新文獻: {title.group(1).strip()}\n  摘要: {clean_summary[:300]}...\n"
            return result if result else "無相關最新文獻。"
        except Exception as e:
            return f"Arxiv 檢索失敗 ({str(e)})"

    # ==========================================
    # 策略二：Web Search - 自動搜尋領域最新資訊
    # ==========================================
    def _fetch_web(self, query):
        try:
            safe_query = urllib.parse.quote(query)
            # 使用 Wikipedia API 作為輕量化、免 Key 的網頁搜尋替代方案
            url = f"https://zh.wikipedia.org/w/api.php?action=query&list=search&srsearch={safe_query}&utf8=&format=json"
            res = requests.get(url, timeout=5)
            res.raise_for_status()
            data = res.json()
            result = ""
            for item in data.get("query", {}).get("search", [])[:2]:
                # 移除 HTML 標籤
                snippet = re.sub(r'<[^>]+>', '', item.get("snippet", ""))
                result += f"- {item.get('title')}: {snippet}...\n"
            return result if result else "無相關網頁資訊。"
        except Exception as e:
            return f"網頁檢索失敗 ({str(e)})"

    # ==========================================
    # 匯整外部知識 (知識截斷解決方案)
    # ==========================================
    async def _gather_external_knowledge(self):
        knowledge_blocks = []
        
        # 執行策略一
        if self.knowledge_config.get("enable_rag") and self.paper.field:
            rag_text = await asyncio.to_thread(self._fetch_arxiv, self.paper.field)
            if rag_text and "無相關" not in rag_text:
                knowledge_blocks.append(f"【學術資料庫檢索結果 (Arxiv 最新發表)】\n{rag_text}")
        
        # 執行策略二
        if self.knowledge_config.get("enable_web_search") and self.paper.field:
            web_text = await asyncio.to_thread(self._fetch_web, self.paper.field)
            if web_text and "無相關" not in web_text:
                knowledge_blocks.append(f"【聯網搜尋最新趨勢 (Web Search)】\n{web_text}")
                
        # 執行策略三 (加入使用者平台動態上傳的文獻)
        if self.knowledge_config.get("enable_reference_upload") and getattr(self.paper, "references", ""):
            # 限制補充文獻長度，避免撐爆 Context Window
            knowledge_blocks.append(f"【使用者動態補充之最新參考文獻】\n{self.paper.references[:15000]}") 
            
        if knowledge_blocks:
            return "\n\n".join(knowledge_blocks)
        return ""

    async def run_round_1(self):
        """第一輪：獨立審查"""
        # 獲取解決時間落差的外部知識
        external_knowledge = await self._gather_external_knowledge()
        
        tasks = []
        for reviewer in self.reviewers:
            system_prompt = (
                f"You are {reviewer.name}, an expert in {reviewer.expertise}. "
                f"Your style is: {reviewer.style}. "
                "Please review the following paper."
            )
            # 截斷過長文本以確保安全
            paper_text = f"Title: {self.paper.title}\nContent:\n{self.paper.content[:5000]}..." 
            
            # 將外部知識無縫注入 Prompt
            if external_knowledge:
                user_prompt = (
                    f"【系統提示：為了解決知識截斷問題，以下提供最新外部參考資訊，請務必將此最新資訊納入審查考量】\n"
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
            # 整理其他委員的意見
            other_reviews = "\n\n".join([
                f"{r.name}'s review:\n{self.history['round_1'][r.name]}" 
                for r in self.reviewers if r != reviewer
            ])
            
            system_prompt = (
                f"You are {reviewer.name}. Read the reviews of your colleagues and provide your rebuttal or agreement. "
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
        # 指定第一位委員作為主席 (Chair)
        chair = self.reviewers[0]
        
        all_prior_context = "Round 1:\n" + "\n".join([f"{k}: {v}" for k, v in self.history["round_1"].items()]) + \
                            "\n\nRound 2:\n" + "\n".join([f"{k}: {v}" for k, v in self.history["round_2"].items()])

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
        
        # 預設先將原始文字存入歷史紀錄
        self.history["round_3"]["Final Verdict"] = response

        # 強健的 JSON 解析機制
        try:
            # 嘗試擷取大括號內的 JSON 內容 (防止 LLM 雞婆加上 Markdown 標記)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            json_str = json_match.group() if json_match else response
            
            parsed_data = json.loads(json_str)
            
            # 安全提取數據，若缺少則給予預設值 0.0
            self.review_stats["avg_contribution"] = float(parsed_data.get("avg_contribution", 0.0))
            self.review_stats["avg_deficiencies"] = float(parsed_data.get("avg_deficiencies", 0.0))
            self.review_stats["avg_robustness"] = float(parsed_data.get("avg_robustness", 0.0))
            
            # 將 UI 顯示的結論替換為 JSON 中的 summary
            self.history["round_3"]["Final Verdict"] = parsed_data.get("summary", "無法從 JSON 中提取 summary。")

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            # 若模型輸出非 JSON 格式 (例如降級為模擬模式時)，保留預設的 0.0 分並顯示錯誤提示
            self.history["round_3"]["Final Verdict"] = f"⚠️ 模型未輸出標準 JSON 格式，無法解析評分。\n\n**原始輸出內容：**\n{response}"

        return self.history["round_3"]