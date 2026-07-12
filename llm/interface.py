# llm/interface.py

import asyncio
import json
import os
import subprocess
import sys
import time

import requests


def _detect_blackwell() -> bool:
    """偵測是否為 NVIDIA Blackwell (50 系) 顯卡。"""
    try:
        if os.name == "nt":
            # 透過 PowerShell WMI 查詢，避免提前初始化 CUDA runtime 鎖住裝置
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance -ClassName Win32_VideoController | Select-Object -ExpandProperty Name"],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True, text=True,
            )
        if res.returncode == 0:
            gpu_info = res.stdout.strip().lower()
            return any(k in gpu_info for k in ("5090", "5080", "5070", "blackwell"))
    except Exception:
        pass
    return False


def _blackwell_force_cpu_enabled() -> bool:
    """由 config.json 的 local.force_cpu_on_blackwell 控制防閃退 CPU 模式。

    (取代舊版寫死在程式碼中的 `_has_blackwell = False` 覆寫；
    換上相容的 llama-cpp 編譯版後，將設定保持 false 即可全速使用 GPU。)
    """
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return bool(cfg.get("local", {}).get("force_cpu_on_blackwell", False))
    except Exception:
        return False


_has_blackwell = _detect_blackwell() and _blackwell_force_cpu_enabled()

original_cuda_val = os.environ.get("CUDA_VISIBLE_DEVICES")
if _has_blackwell:
    # 提前在 Llama 模組載入前關閉 GPU
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

try:
    from llama_cpp import Llama
    HAS_LLAMA_CPP = True
except ImportError:
    HAS_LLAMA_CPP = False
finally:
    if _has_blackwell:
        if original_cuda_val is not None:
            os.environ["CUDA_VISIBLE_DEVICES"] = original_cuda_val
        else:
            del os.environ["CUDA_VISIBLE_DEVICES"]

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class LLMInterface:
    def __init__(self, config_path: str = "config.json"):
        # 優先查找工作目錄下的 config.json，再查找打包內的
        if os.path.exists(config_path):
            self.config_path = config_path
        else:
            self.config_path = resource_path(config_path)
            
        self.config = self._load_config(self.config_path)
        self.mode = self.config.get("llm_mode", "mock")
        self.local_llm = None

        if self.mode == "local":
            if not HAS_LLAMA_CPP:
                print("警告：未安裝 llama-cpp-python，無法使用本地模型。")
                self.mode = "mock"
            else:
                model_path = self.config.get("local", {}).get("model_path", "")
                
                # 路徑處理：優先查看 CWD，再查看 _internal 內部
                if not os.path.exists(model_path):
                    potential_path = resource_path(model_path)
                    if os.path.exists(potential_path):
                        model_path = potential_path
                    else:
                        print(f"錯誤：找不到本地模型檔案 {model_path} 或 {potential_path}，將降級為模擬模式。")
                        self.mode = "mock"
                        return

                if self.mode != "mock":
                    local_cfg = self.config.get("local", {})
                    n_ctx = local_cfg.get("n_ctx", 4096)
                    use_gpu = local_cfg.get("use_gpu", True)
                    
                    # Auto-detect Blackwell/50-series to avoid fatal crashes in llama-cpp
                    if use_gpu and _has_blackwell:
                        print("自動偵測到高階 Blackwell 架構顯卡，為避免編譯版不相容，強制卸載 GPU (改用純 CPU)")
                        use_gpu = False
                    
                    try:
                        if use_gpu:
                            # 嘗試開啟 GPU 加速 (n_gpu_layers=-1 表示全卸載至 GPU)
                            self.local_llm = Llama(
                                model_path=model_path, 
                                n_ctx=n_ctx, 
                                n_gpu_layers=-1,
                                verbose=False
                            )
                        else:
                            # 使用純 CPU 模式，避免部分高階顯卡出現致命 CUDA Error 閃退
                            # 若 Llama 模組編譯了 CUDA 後端，即便 n_gpu_layers=0 仍會觸發 init 導致崩潰，
                            # 因此利用環境變數徹底隱蔽 GPU。
                            original_cuda = os.environ.get("CUDA_VISIBLE_DEVICES")
                            os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
                            
                            try:
                                self.local_llm = Llama(
                                    model_path=model_path, 
                                    n_ctx=n_ctx, 
                                    n_gpu_layers=0,
                                    verbose=False
                                )
                            finally:
                                if original_cuda is not None:
                                    os.environ["CUDA_VISIBLE_DEVICES"] = original_cuda
                                else:
                                    del os.environ["CUDA_VISIBLE_DEVICES"]
                                    
                    except Exception as e:
                        print(f"模型載入失敗：{e}")
                        self.mode = "mock"

    def _load_config(self, path: str) -> dict:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"llm_mode": "mock"}

    def get_input_token_budget(self) -> int:
        """回傳目前引擎大約可用的「輸入」token 數，供 orchestrator 動態配置論文長度。"""
        if self.mode == "local":
            local_cfg = self.config.get("local", {})
            n_ctx = int(local_cfg.get("n_ctx", 4096))
            max_out = int(local_cfg.get("max_tokens", 1024))
            return max(n_ctx - max_out, 2048)
        if self.mode == "ollama":
            # Ollama 預設 context 常為 8k；保守估計
            return 8192
        if self.mode == "cloud":
            provider = self.config.get("cloud", {}).get("provider", "openai")
            # Gemini 支援極長上下文；其他 OpenAI 相容服務多為 128k
            return 200000 if provider == "gemini" else 100000
        if self.mode == "gemini_native":
            return 200000
        return 8192  # mock 或未知模式

    @property
    def hardware_info(self) -> str:
        """ 返回推論硬體狀態 """
        if self.mode == "cloud":
            return "☁️ Cloud API"
        if self.mode == "gemini_native":
            return "✨ Gemini Native API"
        if self.mode == "mock":
            return "🛠️ Mock (CPU)"
        if self.mode == "ollama":
            # 檢查 Ollama 是否在運行
            ollama_host = self.config.get("ollama", {}).get("host", "http://localhost:11434")
            try:
                # 呼叫 Ollama 的 tags API 檢查健康度
                resp = requests.get(f"{ollama_host}/api/tags", timeout=2)
                if resp.status_code == 200:
                    return "🐑 Ollama (Running)"
                return "🐑 Ollama (API Error)"
            except:
                return "❌ Ollama (Not Found / Offline)"
        
        if self.local_llm:
            try:
                # llama-cpp-python context_params 有 n_gpu_layers
                # 這裡使用 getattr 安全讀取，避免舊版本報錯
                n_gpu = getattr(self.local_llm.context_params, 'n_gpu_layers', -2)
                if n_gpu != 0:
                    return f"💻 GPU (Offloaded {n_gpu} layers)"
            except:
                pass
            return "💻 Local CPU"
        return "❌ 未載入"

    async def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        if self.mode == "local" and self.local_llm:
            return await asyncio.to_thread(self._generate_local_sync, system_prompt, user_prompt)
        elif self.mode == "ollama":
            return await asyncio.to_thread(self._generate_ollama_sync, system_prompt, user_prompt)
        elif self.mode == "cloud":
            return await self._generate_cloud_async(system_prompt, user_prompt)
        elif self.mode == "gemini_native":
            return await self._generate_gemini_native_async(system_prompt, user_prompt)
        else:
            return await self._generate_mock_async(system_prompt, user_prompt)

    async def _generate_gemini_native_async(self, system_prompt: str, user_prompt: str) -> str:
        gemini_config = self.config.get("gemini_native", {})
        api_key = gemini_config.get("api_key", "").strip()
        model_name = gemini_config.get("model_name", "").strip()
        
        # 💡 智慧金鑰與模型名稱共用邏輯：
        # 如果使用者在左側 UI 中設定了 Gemini，其金鑰與模型名稱會儲存在 cloud 區塊中。
        # 原生 SDK 模式（gemini_native）應優先共用/繼承使用者在介面上設定的值！
        cloud_config = self.config.get("cloud", {})
        
        # 1. 繼承金鑰
        if not api_key or "YOUR" in api_key or api_key == "":
            cloud_key = cloud_config.get("api_key", "").strip()
            if cloud_key and "YOUR" not in cloud_key:
                api_key = cloud_key
                
        # 2. 繼承模型名稱
        # 如果原生區塊的模型名稱為空、或是預設的舊模型名稱，且使用者在 UI 上設定了新模型名稱，則直接共用 UI 設定
        if not model_name or model_name == "gemini-1.5-pro-latest" or model_name == "gemini-1.5-flash":
            cloud_model = cloud_config.get("model_name", "").strip()
            if cloud_model:
                model_name = cloud_model
                
        # 3. 確保有預設值
        if not model_name:
            model_name = "gemini-1.5-flash"
            
        if not api_key or "YOUR" in api_key or api_key == "":
            return "錯誤：請先在參數設定中填入有效的 Gemini API Key。"
            
        return await asyncio.to_thread(self._generate_gemini_sync, api_key, model_name, system_prompt, user_prompt)

    def _generate_ollama_sync(self, system_prompt: str, user_prompt: str) -> str:
        """ 透過 Ollama API 進行推論 """
        ollama_config = self.config.get("ollama", {})
        host = ollama_config.get("host") or ollama_config.get("base_url", "http://localhost:11434")
        host = host.rstrip("/")
        model = ollama_config.get("model_name", "llama3.1")
        api_key = ollama_config.get("api_key", "").strip()
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": ollama_config.get("max_tokens", 4096)
            },
            "keep_alive": ollama_config.get("keep_alive", "30m"),
        }
        
        try:
            response = requests.post(
                f"{host}/api/chat",
                headers=headers,
                json=payload,
                timeout=int(ollama_config.get("timeout", 300)),
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "").strip()
        except Exception as e:
            return f"【Ollama 推論錯誤】：{str(e)}\n請確認 Ollama 已啟動且已下載 '{model}' 模型。"

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

        # 新世代 / 預覽 / 實驗版模型僅支援 v1beta 介面
        is_beta_model = any(x in model_name.lower() for x in ["preview", "exp", "beta", "2.0", "3.0", "3.1", "3.5", "4.0"])
        api_version = "v1beta" if is_beta_model else "v1"
        url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model_name}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}

        combined_prompt = f"系統指令：\n{system_prompt}\n\n請根據以上指令處理以下內容：\n{user_prompt}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": combined_prompt}]}],
            "generationConfig": {"temperature": 0.7},
        }

        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)

                # 處理 429 (Rate Limit) 或 503 (Overloaded)
                if response.status_code in [429, 503]:
                    import random
                    base_wait = (2 ** attempt) * 5 + random.uniform(0, 1)
                    wait_time = base_wait
                    try:
                        response_data = response.json()
                        error_data = response_data.get("error", {})
                        retry_info = error_data.get("details", [])
                        for detail in retry_info:
                            if detail.get("@type") == "type.googleapis.com/google.rpc.RetryInfo":
                                retry_delay_str = detail.get("retryDelay", "5s")
                                wait_time = float(retry_delay_str.rstrip("s"))
                                if wait_time < 2:
                                    wait_time = base_wait
                                break
                        if error_data.get("status") == "RESOURCE_EXHAUSTED":
                            error_msg = error_data.get("message", "")
                            has_retry_delay = any(d.get("@type") == "type.googleapis.com/google.rpc.RetryInfo" for d in retry_info)
                            if "limit: 0" in error_msg and not has_retry_delay:
                                return f"【Gemini 額度耗盡】：您的每日 API 配額已用完。請更換 API Key 或明日再試。\n詳細訊息：{error_msg}"
                    except Exception:
                        pass
                    if attempt < max_retries - 1:
                        status_name = "速率限制 (429)" if response.status_code == 429 else "伺服器忙碌 (503)"
                        print(f"Gemini {status_name}，等待 {wait_time:.2f} 秒後進行第 {attempt+2} 次重試...")
                        time.sleep(wait_time)
                        continue

                if response.status_code != 200:
                    # 404 可能是 v1 不支援該模型，改試 v1beta
                    if response.status_code == 404:
                        url_beta = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                        response = requests.post(url_beta, headers=headers, json=payload, timeout=60)
                        if response.status_code != 200:
                            return f"【Gemini API 錯誤】：找不到模型或 API 版本不支援。請確認模型名稱 '{model_name}' 是否正確。({response.status_code})"
                    else:
                        return f"【Gemini API 錯誤】：{response.status_code} - {response.text}"

                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    detail = data.get("promptFeedback", data)
                    return f"【Gemini 沒給出回應】：{detail}"
                parts = candidates[0].get("content", {}).get("parts", [])
                result = "".join(part.get("text", "") for part in parts).strip()
                if not result:
                    return "【Gemini API 錯誤】：模型回應為空。"
                return result

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return f"【連線錯誤】：{str(e)}"

        return "【Gemini 錯誤】：已達最大重試次數，仍受速率限制。"

    def list_models(self, api_key: str = None) -> str:
        """列出 Gemini API Key 可用的所有模型 (逗號分隔字串，用於除錯與 UI 顯示)。"""
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
                return "、".join(models) if models else "找不到任何模型。"
            else:
                return f"無法取得模型清單 ({response.status_code}): {response.text}"
        except Exception as e:
            return f"連線失敗: {str(e)}"

    @staticmethod
    def models_endpoint_from_chat_url(api_url: str) -> str:
        """從 chat/completions 端點推導 /models 端點。

        例：https://api.deepseek.com/v1/chat/completions → https://api.deepseek.com/v1/models
        """
        api_url = (api_url or "").strip().rstrip("/")
        if api_url.endswith("/chat/completions"):
            return api_url[: -len("/chat/completions")] + "/models"
        # 已是 base (如 .../v1) 的情況
        return api_url + "/models"

    def list_openai_models(self, api_key: str, api_url: str = None):
        """列出 OpenAI 相容服務可用的模型。

        成功回傳模型 id 的 list[str] (依字母排序)；失敗回傳錯誤訊息字串。
        適用 OpenAI / DeepSeek / Groq / OpenRouter 等相容端點。
        """
        api_key = (api_key or "").strip()
        if not api_key:
            return "錯誤：未設定有效 API Key。"

        if not api_url:
            api_url = self.config.get("cloud", {}).get("api_url", "https://api.openai.com/v1/chat/completions")
        url = self.models_endpoint_from_chat_url(api_url)

        try:
            response = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
            if response.status_code != 200:
                return f"無法取得模型清單 ({response.status_code}): {response.text[:300]}"
            data = response.json()
            items = data.get("data", data.get("models", []))
            models = []
            for m in items:
                mid = m.get("id") if isinstance(m, dict) else str(m)
                if mid:
                    models.append(mid)
            if not models:
                return "找不到任何模型。"
            return sorted(models)
        except Exception as e:
            return f"連線失敗: {str(e)}"

    def _generate_cloud_sync(self, api_key: str, model_name: str, api_url: str, system_prompt: str, user_prompt: str) -> str:
        url = api_url
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
        }

        # 增加重試次數與等待時間，以應對嚴格的 TPM 限制
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                if response.status_code == 429:
                    wait_time = (attempt + 1) * 20
                    print(f"收到 429 (TPM 限制)，正在等待 {wait_time} 秒後重試...")
                    time.sleep(wait_time)
                    continue
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                if attempt == max_retries - 1:
                    return f"【雲端 API 錯誤】：{str(e)}"
                time.sleep(5)
        return "【雲端 API 錯誤】：已嘗試多次重試，但仍受限於 API 提供商的流量限制 (TPM)。建議更換 Higher Tier 的 API Key，或切換至本地模型。"

    async def _generate_mock_async(self, system_prompt: str, user_prompt: str) -> str:
        await asyncio.sleep(1)
        return "【模擬回應】這是一則預設的測試建議。"
