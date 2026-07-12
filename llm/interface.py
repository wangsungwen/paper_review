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
        host = ollama_config.get("host", "http://localhost:11434")
        model = ollama_config.get("model_name", "llama3.1")
        
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
            }
        }
        
        try:
            response = requests.post(f"{host}/api/chat", json=payload, timeout=120)
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
        
        # Google Gemini API (REST) - 智慧 API 版本選擇：新世代、預覽版、實驗版模型僅支援 v1beta 介面，直接導向以享受自動重試與速率限制退避
        is_beta_model = any(x in model_name.lower() for x in ["preview", "exp", "beta", "2.0", "3.0", "3.1", "3.5", "4.0"])
        api_version = "v1beta" if is_beta_model else "v1"
        url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model_name}:generateContent?key={api_key}"
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
