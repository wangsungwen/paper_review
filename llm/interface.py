# llm/interface.py

import json
import os
import asyncio
import requests
import time

try:
    from llama_cpp import Llama
    HAS_LLAMA_CPP = True
except ImportError:
    HAS_LLAMA_CPP = False

class LLMInterface:
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.mode = self.config.get("llm_mode", "mock")
        self.local_llm = None

        if self.mode == "local":
            if not HAS_LLAMA_CPP:
                print("警告：未安裝 llama-cpp-python，無法使用本地模型。")
                self.mode = "mock"
            else:
                model_path = self.config.get("local", {}).get("model_path", "")
                if os.path.exists(model_path):
                    n_ctx = self.config.get("local", {}).get("n_ctx", 4096)
                    try:
                        self.local_llm = Llama(model_path=model_path, n_ctx=n_ctx, verbose=False)
                    except Exception as e:
                        print(f"載入模型失敗：{e}")
                        self.mode = "mock"
                else:
                    print(f"錯誤：找不到本地模型檔案 {model_path}，將降級為模擬模式。")
                    self.mode = "mock"

    def _load_config(self, path: str) -> dict:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"llm_mode": "mock"}

    async def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        if self.mode == "local" and self.local_llm:
            return await asyncio.to_thread(self._generate_local_sync, system_prompt, user_prompt)
        elif self.mode == "cloud":
            return await self._generate_cloud_async(system_prompt, user_prompt)
        else:
            return await self._generate_mock_async(system_prompt, user_prompt)

    def _generate_local_sync(self, system_prompt: str, user_prompt: str) -> str:
        if not self.local_llm:
            return "錯誤：本地模型尚未載入。"
        local_config = self.config.get("local", {})
        context_window = local_config.get("n_ctx", 4096)
        max_tokens = local_config.get("max_tokens", 1024)
        full_system = f"System: {system_prompt}"
        full_user = f"User: {user_prompt}"
        estimated_sys_tokens = len(full_system) // 2
        estimated_user_tokens = len(full_user) // 2
        if (estimated_sys_tokens + estimated_user_tokens + max_tokens) > context_window:
            allowed_user_chars = (context_window - max_tokens - estimated_sys_tokens - 100) * 2
            if allowed_user_chars > 0 and len(user_prompt) > allowed_user_chars:
                user_prompt = user_prompt[:allowed_user_chars] + "\n...(此處因長度限制而截斷)..."
        prompt = f"System: {system_prompt}\nUser: {user_prompt}\nAssistant:"
        try:
            response = self.local_llm(
                prompt,
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=0.9,
                stop=["User:", "System:", "<|eot_id|>"],
                echo=False
            )
            return response['choices'][0]['text'].strip()
        except Exception as e:
            error_msg = str(e)
            if "context window" in error_msg.lower() or "decode" in error_msg.lower():
                return f"【模型限制】論文內容過長，超過處理上限。"
            return f"【推論錯誤】：{error_msg}"

    async def _generate_cloud_async(self, system_prompt: str, user_prompt: str) -> str:
        cloud_config = self.config.get("cloud", {})
        api_key = cloud_config.get("api_key", "")
        model_name = cloud_config.get("model_name", "gpt-4o")
        if not api_key or "YOUR_CLOUD_API_KEY_HERE" in api_key:
            return "錯誤：請先在 config.json 中填入有效的 OpenAI API Key。"
        return await asyncio.to_thread(self._generate_cloud_sync, api_key, model_name, system_prompt, user_prompt)

    def _generate_cloud_sync(self, api_key: str, model_name: str, system_prompt: str, user_prompt: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7
        }

        # 增加重試次數與等待時間，以應對嚴格的 TPM 限制
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                if response.status_code == 429:
                    # 隨著重試次數增加，等待時間大幅拉長 (指數退避)
                    wait_time = (attempt + 1) * 20 
                    print(f"收到 429 (TPM 限制)，正在等待 {wait_time} 秒後重試...")
                    time.sleep(wait_time)
                    continue
                response.raise_for_status()
                data = response.json()
                return data['choices'][0]['message']['content'].strip()
            except Exception as e:
                if attempt == max_retries - 1:
                    return f"【雲端 API 錯誤】：{str(e)}"
                time.sleep(5)
        return "【雲端 API 錯誤】：已嘗試多次重試，但仍受限於 API 提供商的流量限制 (TPM)。建議更換 Higher Tier 的 API Key，或切換至本地模型。"

    async def _generate_mock_async(self, system_prompt: str, user_prompt: str) -> str:
        await asyncio.sleep(1)
        return "【模擬回應】這是一則預設的測試建議。"