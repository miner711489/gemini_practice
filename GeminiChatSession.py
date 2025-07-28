import os
import google.generativeai as genai
from google.api_core import exceptions
from typing import List, Optional, Dict, Any

# 假設 genai 已在您的程式某處設定好 API Key
# genai.configure(api_key="YOUR_API_KEY")


class GeminiChatSession:
    """
    一個封裝 Gemini 多輪對話功能的類別。
    它會維護一個對話歷史，讓模型能夠記住之前的互動。
    """

    def __init__(
        self,
        model_name: str,
        generation_config: Optional[genai.types.GenerationConfig] = None,
        initial_history: Optional[List] = None,
    ):
        """
        初始化對話 session。

        Args:
            model_name (str): 要使用的模型名稱，例如 'gemini-1.5-pro-latest'。
            generation_config (Optional[genai.types.GenerationConfig]): 模型的生成設定。
            initial_history (Optional[List]): 用於開始對話的初始歷史紀錄。
        """

        system_instruction_text = """
        """

        # if api_key:
        #     genai.configure(api_key=api_key)

        print(f"正在初始化模型 '{model_name}'...")
        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction_text,
            safety_settings=None,  # 如果需要安全設置，可以在這裡配置
        )
        self.generation_config = generation_config
        # 使用 model.start_chat() 來建立一個具有狀態的對話物件
        self.chat = self.model.start_chat(history=initial_history or [])
        print("對話 session 已成功啟動。")

    def upload_files(self, file_paths: List[str]) -> List[Any]:
        """
        上傳本地檔案到 Google Gemini API，回傳可用於對話的檔案物件列表。

        Args:
            file_paths (List[str]): 要上傳的本地檔案路徑清單。

        Returns:
            List[Any]: 上傳後的檔案物件列表，可傳給 send_message 的 uploaded_files 參數。
        """
        uploaded_files = []
        for path in file_paths:
            try:
                print(f"正在上傳檔案：{path}")
                # 假設 genai 有 upload_file 方法，實際請依官方 API 調整
                file_obj = genai.upload_file(path)
                uploaded_files.append(file_obj)
                print(f"檔案上傳成功：{path}")
            except Exception as e:
                print(f"檔案上傳失敗：{path}，錯誤：{e}")
        return uploaded_files

    def send_message(self, prompt: str, uploaded_files: Optional[List] = None):
        """
        將 prompt 和選擇性的檔案傳送給模型，並取得回應。
        這個方法會利用 session 的歷史紀錄來進行有上下文的對話。

        Args:
            prompt (str): 使用者的文字輸入。
            uploaded_files (Optional[List]): 使用者上傳的檔案列表 (如果有的話)。

        Returns:
            str: 來自 Gemini 模型的回應文字，或是一則錯誤訊息。
        """
        request_content = [prompt]
        if uploaded_files:
            request_content.extend(uploaded_files)

        if not prompt and not uploaded_files:
            return "錯誤：請提供文字提示或上傳檔案。"

        print(f"\n正在向 Gemini 傳送訊息...")
        try:
            # 對於多輪對話，我們使用 chat.send_message() 而非 model.generate_content()
            response = self.chat.send_message(
                request_content,
                generation_config=self.generation_config,
                # ,safety_settings
            )
            return response.text
        except exceptions.GoogleAPICallError as e:
            return f"呼叫 Google API 時發生錯誤：{e}"
        except Exception as e:
            return f"生成回應時發生未預期的錯誤：{e}"

    @property
    def history(self) -> List:
        """返回目前的對話歷史紀錄。"""
        return self.chat.history
