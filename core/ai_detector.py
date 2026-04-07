# core/ai_detector.py

import re
import json
import requests

class AIDetector:
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.api_key = self.config.get("ai_detector", {}).get("api_key", "")
        self.api_url = self.config.get("ai_detector", {}).get("api_url", "https://api.gptzero.me/v2/predict/text")

    def _load_config(self, path: str) -> dict:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}

    def analyze(self, text: str) -> dict:
        """
        分析文本的 AI 寫作比例，並發送 Request 給真實的 GPTZero API。
        """
        if not text.strip():
            return {"ai_ratio": 0.0, "segments": []}
        
        if not self.api_key or "YOUR_DETECTOR_API_KEY_HERE" in self.api_key:
            return self._mock_analyze(text, "請在 config.json 中設定有效的 GPTZero API Key。")

        try:
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            payload = {"document": text}
            
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # 解析 GPTZero V2 回傳結構
            # 參考結構：{"documents": [{"completely_generated_prob": 0.9, "sentences": [...]}]}
            doc = data.get("documents", [{}])[0]
            ai_ratio = doc.get("completely_generated_prob", 0) * 100
            gpt_sentences = doc.get("sentences", [])
            
            segments = []
            if gpt_sentences:
                for sent in gpt_sentences:
                    prob = sent.get("generated_prob", 0)
                    text_sent = sent.get("sentence", "")
                    
                    if prob > 0.7:
                        color = "#ff9999" if prob > 0.9 else "#ffcccc"
                        segments.append({"text": text_sent, "type": "AI", "color": color})
                    else:
                        segments.append({"text": text_sent, "type": "Human", "color": "transparent"})
            else:
                # 若無句子資訊，回傳成整塊
                segments.append({"text": text, "type": "Mixed", "color": "transparent"})

            return {
                "ai_ratio": round(ai_ratio, 2),
                "segments": segments
            }

        except requests.exceptions.RequestException as e:
            return self._mock_analyze(text, f"API 連線或請求失敗：{str(e)} (切換回模擬模式)")
        except Exception as e:
            return self._mock_analyze(text, f"偵測過程發生未知錯誤：{str(e)} (切換回模擬模式)")

    def _mock_analyze(self, text: str, reason: str) -> dict:
        # 保留原有的模擬邏輯作為備援或未設定 Key 時的呈現
        sentences = re.split(r'(?<=[。！？.!?\n])', text)
        segments = []
        for sent in sentences:
            if not sent.strip():
                segments.append({"text": sent, "type": "Human", "color": "transparent"})
                continue
            import random
            ai_probability = random.random()
            if ai_probability > 0.8:
                color = "#ff9999" if ai_probability > 0.95 else "#ffcccc"
                segments.append({"text": sent, "type": "AI", "color": color})
            else:
                segments.append({"text": sent, "type": "Human", "color": "transparent"})
        
        return {
            "ai_ratio": 10.0, # 固定一個模擬數值代表模式
            "segments": segments,
            "notice": reason
        }