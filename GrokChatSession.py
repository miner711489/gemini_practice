import os
import time
import random
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
import base64
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    raise ImportError("請安裝 openai 套件: pip install openai")


class GrokChatSession:
    """
    一個封裝 xAI Grok 多輪對話功能的類別。
    它會維護一個對話歷史，讓模型能夠記住之前的互動。
    xAI API 與 OpenAI API 完全相容，因此使用 OpenAI SDK。
    """

    def printLog(self, obj: Any, mustShow: bool = True):
        showLog = False
        if mustShow or showLog:
            print(obj)

    def __init__(
        self,
        api_key: str,
        model_name: str = "grok-4-0709",
        generation_config: Optional[Dict] = None,
        initial_history: Optional[List[Dict]] = None,
    ):
        """
        初始化對話 session。

        Args:
            api_key (str): xAI API 金鑰
            model_name (str): 要使用的模型名稱，例如 'grok-4-0709', 'grok-4-fast'
            generation_config (Optional[Dict]): 模型的生成設定，對應 OpenAI 的參數
            initial_history (Optional[List[Dict]]): 用於開始對話的初始歷史紀錄
        """

        system_instruction_text = """小說產生原則
沒有字數限制，但是要在保證文章品質的情況下盡可能的輸出更多文字與延長篇幅，你需要寫得非常詳細，且避免重複和無聊内容。
盡可能的像人與人之間的對話，包含對話和聲音描寫，描寫心理變化和感受，使用通俗易懂的語言，且要有一定對話內容與連續性。
角色之間的互動更具臨場感。若角色之間有衝突或情感波動，務必鋪陳心理變化與反應過程，讓讀者能感受到角色內心的拉扯與真實性。
避免過度文藝化表達，使用直白具體的描述方式，甚至允許部分粗俗描述方式。
場景要夠震撼，多細節才能顯得真實，給人身臨其境的感受。
故事要符合邏輯。所有內容融為一體,不分點輸出,但可以分段，不要自作主張地分章節，我需要連續的文章，上下的對話可以貫通的那種。
只需要產生我要求的小說內容，不要提供其他多餘回復或建議內容
使用繁體中文產生小說
        """

        # 初始化 OpenAI client，但指向 xAI 的端點
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )
        
        self.model_name = model_name
        
        # 設定默認的生成參數
        self.default_generation_config = {
            "temperature": 0.7,
            "max_tokens": 4000,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0
        }
        
        if generation_config:
            self.default_generation_config.update(generation_config)
        
        self.generation_config = self.default_generation_config

        # 初始化對話歷史
        self.messages = []
        
        # 添加系統指令
        self.messages.append({
            "role": "system",
            "content": system_instruction_text
        })
        
        # 如果有初始歷史，加入對話中
        if initial_history:
            self.messages.extend(initial_history)

        self.printLog(f"正在初始化 Grok 模型 '{model_name}'...")
        self.printLog("Grok 對話 session 已成功啟動。")

    def encode_image_to_base64(self, image_path: str) -> str:
        """
        將圖片檔案編碼為 base64 字串
        
        Args:
            image_path (str): 圖片檔案路徑
            
        Returns:
            str: base64 編碼的圖片字串
        """
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                
            # 取得檔案副檔名來判斷 MIME type
            file_extension = Path(image_path).suffix.lower()
            mime_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg', 
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            mime_type = mime_type_map.get(file_extension, 'image/jpeg')
            
            return f"data:{mime_type};base64,{encoded_string}"
        except Exception as e:
            self.printLog(f"編碼圖片時發生錯誤: {e}")
            return None

    def upload_files(self, file_paths: List[str]) -> List[Dict]:
        """
        處理本地檔案，轉換為 Grok API 可接受的格式。
        主要處理圖片檔案，將其編碼為 base64 格式。

        Args:
            file_paths (List[str]): 要處理的本地檔案路徑清單

        Returns:
            List[Dict]: 處理後的檔案資料列表，可傳給 send_message 的 uploaded_files 參數
        """
        processed_files = []
        
        supported_image_types = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        
        for path in file_paths:
            try:
                file_path = Path(path)
                if not file_path.exists():
                    self.printLog(f"檔案不存在: {path}")
                    continue
                    
                file_extension = file_path.suffix.lower()
                
                if file_extension in supported_image_types:
                    # 處理圖片檔案
                    self.printLog(f"正在處理圖片檔案：{path}")
                    base64_image = self.encode_image_to_base64(path)
                    if base64_image:
                        processed_files.append({
                            "type": "image_url",
                            "image_url": {
                                "url": base64_image
                            }
                        })
                        self.printLog(f"✅ 圖片檔案處理成功：{path}")
                    else:
                        self.printLog(f"❌ 圖片檔案處理失敗：{path}")
                else:
                    self.printLog(f"⚠️  不支援的檔案類型：{path} (目前只支援圖片檔案)")
                    
            except Exception as e:
                self.printLog(f"處理檔案時發生錯誤：{path}，錯誤：{e}")

        self.printLog(f"檔案處理完成，共處理 {len(processed_files)} 個檔案")
        return processed_files

    def send_message(self, prompt: str, uploaded_files: Optional[List[Dict]] = None):
        """
        將 prompt 和選擇性的檔案傳送給 Grok 模型，並取得回應。
        這個方法會利用 session 的歷史紀錄來進行有上下文的對話。

        Args:
            prompt (str): 使用者的文字輸入
            uploaded_files (Optional[List[Dict]]): 使用者上傳的檔案列表 (如果有的話)

        Returns:
            str: 來自 Grok 模型的回應文字，或是一則錯誤訊息
        """
        if not prompt and not uploaded_files:
            return "錯誤：請提供文字提示或上傳檔案。"

        # 構建訊息內容
        message_content = []
        
        # 添加文字內容
        if prompt:
            message_content.append({
                "type": "text",
                "text": prompt
            })
        
        # 添加檔案內容 (主要是圖片)
        if uploaded_files:
            message_content.extend(uploaded_files)

        # 將使用者訊息加入歷史
        user_message = {
            "role": "user",
            "content": message_content if len(message_content) > 1 else prompt
        }
        self.messages.append(user_message)

        max_retries = 5

        for attempt in range(max_retries):
            current_datetime = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            self.printLog(f"\n正在向 Grok 傳送訊息，{current_datetime}...")
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=self.messages,
                    **self.generation_config
                )
                
                # 取得回應內容
                assistant_message_content = response.choices[0].message.content
                
                # 將助理回應加入歷史
                assistant_message = {
                    "role": "assistant", 
                    "content": assistant_message_content
                }
                self.messages.append(assistant_message)
                
                current_datetime = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                self.printLog(f"\nGrok 已回傳訊息，{current_datetime}...")
                return assistant_message_content
                
            except Exception as e:
                error_message = str(e)
                log_time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                
                # 檢查是否是可重試的錯誤
                retryable_errors = [
                    "rate_limit_exceeded", 
                    "server_error", 
                    "timeout",
                    "internal_server_error",
                    "service_unavailable"
                ]
                
                is_retryable = any(error_type in error_message.lower() for error_type in retryable_errors)
                
                if is_retryable and attempt < max_retries - 1:
                    self.printLog(
                        f"[{log_time}]呼叫 Grok API 時發生可重試錯誤 (第 {attempt + 1} 次失敗): {e}",
                        True,
                    )
                    # 指數退避邏輯
                    wait_time = min(10 * (2 ** attempt), 60)  # 最大等待 60 秒
                    self.printLog(f"將在 {wait_time} 秒後重試...", True)
                    time.sleep(wait_time)
                else:
                    if attempt >= max_retries - 1:
                        self.printLog(f"[{log_time}]已達到最大重試次數，放棄操作。", True)
                        return f"呼叫 Grok API 失敗，已重試 {max_retries} 次後放棄。最後錯誤：{e}"
                    else:
                        self.printLog(f"[{log_time}]發生不可重試的錯誤: {e}", True)
                        return f"呼叫 Grok API 時發生錯誤：{e}"

    @property
    def history(self) -> List[Dict]:
        """返回目前的對話歷史紀錄。"""
        return self.messages.copy()
        
    def clear_history(self):
        """清空對話歷史，但保留系統指令。"""
        system_message = next((msg for msg in self.messages if msg["role"] == "system"), None)
        self.messages = []
        if system_message:
            self.messages.append(system_message)
        self.printLog("對話歷史已清空")
        
    def save_history(self, file_path: str):
        """將對話歷史儲存到 JSON 檔案。"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2)
            self.printLog(f"對話歷史已儲存到: {file_path}")
        except Exception as e:
            self.printLog(f"儲存對話歷史時發生錯誤: {e}")
            
    def load_history(self, file_path: str):
        """從 JSON 檔案載入對話歷史。"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.messages = json.load(f)
            self.printLog(f"對話歷史已從 {file_path} 載入")
        except Exception as e:
            self.printLog(f"載入對話歷史時發生錯誤: {e}")


# 使用範例
if __name__ == "__main__":
    # 初始化 Grok 對話 session
    # 請替換為你的 xAI API 金鑰
    api_key = "your-xai-api-key-here"
    
    # 建立對話 session
    grok_session = GrokChatSession(
        api_key=api_key,
        model_name="grok-4-0709",  # 或使用 "grok-4-fast"
        generation_config={
            "temperature": 0.8,
            "max_tokens": 2000
        }
    )
    
    # 發送文字訊息
    response = grok_session.send_message("請寫一個關於未來世界的短篇小說開頭")
    print("Grok 回應:", response)
    
    # 如果要處理圖片
    # image_files = grok_session.upload_files(["path/to/your/image.jpg"])
    # response = grok_session.send_message("請描述這張圖片", uploaded_files=image_files)
    
    # 查看對話歷史
    # print("對話歷史:", grok_session.history)