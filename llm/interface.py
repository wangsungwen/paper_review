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

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

import streamlit as st

@st.cache_resource(show_spinner="正在載入 Llama 核心... (這只需執行一次)")
def get_local_llama_instance():
    if not HAS_LLAMA_CPP:
        print("警告：未安裝 llama-cpp-python，無法載入本地模型。")
        return None
        
    try:
        with open("config.json", 'r', encoding='utf-8') as f:
            disk_config = json.load(f)
    except Exception:
        disk_config = {}
        
    model_path = disk_config.get("local", {}).get("model_path", "./local_models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf")
    n_ctx = disk_config.get("local", {}).get("n_ctx", 4096)
    
    # 解析打包環境路徑
    if not os.path.exists(model_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        potential_path = os.path.join(base_path, model_path)
        if os.path.exists(potential_path):
            model_path = potential_path
        else:
            print(f"錯誤：找不到本地模型檔案 {model_path}")
            return None

    try:
        print(f"[System] 正在記憶體常駐載入 Llama 模型: {model_path} (n_ctx: {n_ctx})")
        return Llama(model_path=model_path, n_ctx=n_ctx, verbose=False)
    except Exception as e:
        print(f"載入 Llama 模型失敗：{e}")
        return None

class LLMInterface:
    def __init__(self, config_dict: dict, local_llm_instance=None):
        self.config = config_dict or {}
        self.mode = self.config.get("llm_mode", "mock")
        self.local_llm = local_llm_instance

        if self.mode == "local" and not self.local_llm:
             print("警告：尚未提供本地 LLM 實例，降級為模擬模式。")
             self.mode = "mock"

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
        max_tokens = local_config.get("max_tokens", 2048)
        
        try:
            response = self.local_llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=max_tokens,
                temperature=0.2,
                top_p=0.9,
                stop=["<|eot_id|>", "<|end_of_text|>", "User:", "System:"]
            )
            
            result = response['choices'][0]['message']['content'].strip()
            if not result:
                print("DEBUG - Model returned empty string via chat API.")
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"DEBUG - Inference error: {error_msg}")
            if "context window" in error_msg.lower():
                return "【模型限制】內容過長，超過 Context Window。"
            return f"【推論錯誤】：{error_msg}"

    async def _generate_cloud_async(self, system_prompt: str, user_prompt: str) -> str:
        cloud_config = self.config.get("cloud", {})
        provider = cloud_config.get("provider", "openai")
        api_key = cloud_config.get("api_key", "")
        model_name = cloud_config.get("model_name", "gpt-4o")
        
        if not api_key or "YOUR_CLOUD_API_KEY_HERE" in api_key:
            return "錯誤：請先在 config.json 中填入有效的 API Key。"
            
        if provider == "gemini":
            return await asyncio.to_thread(self._generate_gemini_sync, api_key, model_name, system_prompt, user_prompt)
        else:
            api_url = cloud_config.get("api_url", "https://api.openai.com/v1/chat/completions")
            return await asyncio.to_thread(self._generate_cloud_sync, api_key, model_name, api_url, system_prompt, user_prompt)

    def _generate_gemini_sync(self, api_key: str, model_name: str, system_prompt: str, user_prompt: str) -> str:
        # 確保參數沒有多餘空格，且統一不含 "models/" 前綴
        api_key = api_key.strip()
        model_name = model_name.strip()
        if model_name.startswith("models/"):
            model_name = model_name.replace("models/", "", 1)
        
        # Google Gemini API (REST) - 使用 v1 版本並將系統提示詞併入使用者內容以確保最高相容性
        url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={api_key}"
        headers = {
            "Content-Type": "application/json"
        }
        
        # 建立組合提示詞
        combined_prompt = f"系統指令：\n{system_prompt}\n\n請根據以上指令處理以下內容：\n{user_prompt}"
        
        payload = {
            "contents": [
                {
                    "role": "user", 
                    "parts": [{"text": combined_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.7
            }
        }

        import time

        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                
                # 處理 429 (Rate Limit) 或 503 (Service Unavailable / Overloaded) 錯誤
                if response.status_code in [429, 503]:
                    import random
                    # 預設等待時間 (含退避和隨機抖動)
                    base_wait = (2 ** attempt) * 5 + random.uniform(0, 1)
                    wait_time = base_wait
                    
                    # 嘗試從回應中取得建議的等待時間
                    try:
                        response_data = response.json()
                        error_data = response_data.get("error", {})
                        retry_info = error_data.get("details", [])
                        
                        for detail in retry_info:
                            if detail.get("@type") == "type.googleapis.com/google.rpc.RetryInfo":
                                retry_delay_str = detail.get("retryDelay", "5s")
                                # 處理如 "29.723877525s" 的字串
                                wait_time = float(retry_delay_str.rstrip('s'))
                                # 如果 API 建議的等待時間太短 (例如 0s)，則強制使用基本退避時間
                                if wait_time < 2:
                                    wait_time = base_wait
                                break
                        
                        # 如果是 RESOURCE_EXHAUSTED 且 limit: 0，可能是每日配額已完
                        if error_data.get("status") == "RESOURCE_EXHAUSTED":
                            error_msg = error_data.get("message", "")
                            if "limit: 0" in error_msg:
                                return f"【Gemini 額度耗盡】：您的每日 API 配額已用完。請更換 API Key 或明日再試。\n詳細訊息：{error_msg}"
                    except:
                        pass
                    
                    if attempt < max_retries - 1:
                        status_name = "速率限制 (429)" if response.status_code == 429 else "伺服器忙碌 (503)"
                        print(f"Gemini {status_name}，等待 {wait_time:.2f} 秒後進行第 {attempt+2} 次重試...")
                        time.sleep(wait_time)
                        continue
                
                if response.status_code != 200:
                    # 嘗試第二次機會：如果是 404，可能是 v1 不支援該模型，嘗試切換回 v1beta
                    if response.status_code == 404:
                        url_beta = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                        response = requests.post(url_beta, headers=headers, json=payload, timeout=60)
                        if response.status_code != 200:
                            return f"【Gemini API 錯誤】：找不到模型或 API 版本不支援。請確認模型名稱 '{model_name}' 是否正確。({response.status_code})"
                    else:
                        return f"【Gemini API 錯誤】：{response.status_code} - {response.text}"
                
                data = response.json()
                if 'candidates' not in data or not data['candidates']:
                    return f"【Gemini 沒給出回應】：{str(data)}"
                    
                return data['candidates'][0]['content']['parts'][0]['text'].strip()
                
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return f"【連線錯誤】：{str(e)}"
        
        return "【Gemini 錯誤】：已達最大重試次數，仍受速率限制。"
    def list_models(self, api_key: str = None) -> str:
        """ 嘗試列出該 API Key 可用的所有模型，用於除錯 """
        if not api_key:
            cloud_config = self.config.get("cloud", {})
            api_key = cloud_config.get("api_key", "").strip()
            
        if not api_key or api_key == "YOUR_NEW_GEMINI_API_KEY":
            return "錯誤：未設定有效 API Key。"
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "").replace("models/", "") for m in data.get("models", [])]
                # 過濾掉只支援嵌入或調整的模型，保留支援 generateContent 的
                # 這裡簡單列出所有
                return "、".join(models) if models else "找不到任何模型。"
            else:
                return f"無法取得模型清單 ({response.status_code}): {response.text}"
        except Exception as e:
            return f"連線失敗: {str(e)}"

    def _generate_cloud_sync(self, api_key: str, model_name: str, api_url: str, system_prompt: str, user_prompt: str) -> str:
        url = api_url
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