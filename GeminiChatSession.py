import os
import time
import random
from datetime import datetime
from google import genai
from google.genai import types
from google.api_core import exceptions
from typing import List, Optional, Any, Generator
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import google.api_core.exceptions as google_exceptions


class GeminiChatSession:
    """
    一個封裝 Gemini 多輪對話功能的類別。
    它會維護一個對話歷史，讓模型能夠記住之前的互動。
    """

    def printLog(self, obj: Any, mustShow: bool = True):
        showLog = False
        if mustShow or showLog:
            print(obj)

    def __init__(
        self,
        model_name: str,
        generation_config: Optional[genai.types.GenerationConfig] = None,
        initial_history: Optional[List] = None,
    ):

        system_instruction_path = os.path.join(
            os.path.dirname(__file__), "SystemInstruction.txt"
        )
        if os.path.exists(system_instruction_path):
            with open(system_instruction_path, "r", encoding="utf-8") as f:
                system_instruction_text = f.read()
        else:
            # 如果 SystemInstruction.txt 不存在，則建立並寫入預設內容
            system_instruction_text = """小說產生原則
沒有字數限制，但是要在保證文章品質的情況下盡可能的輸出更多文字與延長篇幅，你需要寫得非常詳細，且避免重複和無聊内容。
盡可能的像人與人之間的對話，包含對話和聲音描寫，描寫心理變化和感受，使用通俗易懂的語言，且要有一定對話內容與連續性。
角色之間的互動更具臨場感。若角色之間有衝突或情感波動，務必鋪陳心理變化與反應過程，讓讀者能感受到角色內心的拉扯與真實性。
避免過度文藝化表達，使用直白具體的描述方式，甚至允許部分粗俗描述方式。
場景要夠震撼，多細節才能顯得真實，給人身臨其境的感受。
故事要符合邏輯。所有內容融為一體,不分點輸出,但可以分段，不要自作主張地分章節，我需要連續的文章，上下的對話可以貫通的那種。
只需要產生我要求的小說內容，不要提供其他多餘回復或建議內容
使用繁體中文產生小說"""

            with open(system_instruction_path, "w", encoding="utf-8") as f:
                f.write(system_instruction_text)

        # 調整安全設定
        safety_settings = [
            {
                "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
        ]

        self.printLog(f"正在初始化模型 '{model_name}'...")
        # self.model = genai.GenerativeModel(
        #     model_name=model_name,
        #     system_instruction=system_instruction_text,
        #     safety_settings=safety_settings,
        # )

        # 這邊要修一下config的部分
        self.generation_config = generation_config
        # self.chat = self.model.start_chat(history=initial_history or [])

        config = types.GenerateContentConfig(
            system_instruction=system_instruction_text,
            temperature=2,
            # safety_settings = safety_settings
        )

        self.client = genai.Client()
        self.chat = self.client.chats.create(
            model=model_name, config=config, history=initial_history or []
        )
        self.printLog("對話 session 已成功啟動。")

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
                # 新寫法，取得已上傳檔案的資訊
                # 將檔案上傳到google
                file_name = os.path.basename(path)

                # 列出專案擁有的 File 中繼資料。
                lstFiles = self.client.files.list()
                if lstFiles:
                    lstFiles = [
                        item
                        for item in lstFiles
                        if getattr(item, "display_name", None) == file_name
                    ]
                    if lstFiles:
                        # 檢查 state 是否為 ACTIVE；state 可能是物件（有 name 屬性）或字串
                        def _is_active(item):
                            state = getattr(item, "state", None)
                            if state is None:
                                return False
                            name = getattr(state, "name", None)
                            if name is not None:
                                return name == "ACTIVE"
                            return str(state).upper() == "ACTIVE"

                        lstFiles = [item for item in lstFiles if _is_active(item)]
                    else:
                        lstFiles = None
                else:
                    lstFiles = None

                if not lstFiles == None:
                    print(f"取得先前上傳的「{file_name}」")
                    uploaded_files.append(lstFiles[0])
                else:
                    print(f"找不到之前上傳的「{file_name}」，開始上傳新的檔案。")
                    uploadFileConfig = {"display_name": file_name}
                    file_obj = self.client.files.upload(
                        file=path, config=uploadFileConfig
                    )
                    uploaded_files.append(file_obj)

            except Exception as e:
                print(f"檔案上傳失敗：{path}，錯誤：{e}")

        print("\n--- 所有檔案上傳請求已提交，開始等待後端處理 ---")
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

        max_retries = 5

        for attempt in range(max_retries):
            current_datetime = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            self.printLog(f"\n正在向 Gemini 傳送訊息，{current_datetime}...")
            try:
                # 對於多輪對話，我們使用 chat.send_message() 而非 model.generate_content()
                response = self.chat.send_message(
                    request_content, config=self.generation_config
                )
                current_datetime = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                self.printLog(f"\nGemini 已回傳訊息，{current_datetime}...")
                return response.text
            except (
                exceptions.InternalServerError,
                exceptions.DeadlineExceeded,
                google_exceptions.ResourceExhausted,
            ) as e:
                log_time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                self.printLog(
                    f"[{log_time}]呼叫 API 時發生可重試錯誤 (第 {attempt + 1} 次失敗): {e}",
                    True,
                )
                if attempt < max_retries - 1:
                    if hasattr(e, "retry_delay") and e.retry_delay is not None:
                        print(f" {e.retry_delay}")

                    self.printLog(f"將在 10 秒後重試...", True)
                    time.sleep(10)
                else:
                    self.printLog("[{log_time}]已達到最大重試次數，放棄操作。", True)
                    return f"呼叫 Google API 失敗，已重試 {max_retries} 次後放棄。最後錯誤：{e}"
            except Exception as e:
                print("=====發生未知錯誤=====")
                print(e)
                return f"生成回應時發生未預期的錯誤：{e}"
            
    def send_message_stream(self, prompt: str, uploaded_files: Optional[List] = None) -> Generator[str, None, None]:
        """
        使用串流方式將 prompt 和選擇性的檔案傳送給模型，實時產生回應。
        這個方法會利用 session 的歷史紀錄來進行有上下文的對話。

        Args:
            prompt (str): 使用者的文字輸入。
            uploaded_files (Optional[List]): 使用者上傳的檔案列表 (如果有的話)。

        Yields:
            str: 逐步從 Gemini 模型接收的回應文字片段。

        Example:
            for chunk in session.send_message_stream("寫一個故事"):
                print(chunk, end="", flush=True)
        """
        request_content = [prompt]
        if uploaded_files:
            request_content.extend(uploaded_files)

        if not prompt and not uploaded_files:
            yield "錯誤：請提供文字提示或上傳檔案。"
            return

        max_retries = 5

        for attempt in range(max_retries):
            current_datetime = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            self.printLog(f"\n正在向 Gemini 傳送訊息（串流模式），{current_datetime}...")
            try:
                # 使用 stream_generate_content 來啟動串流模式
                response_stream = self.chat.send_message_stream(
                    request_content, config=self.generation_config
                )
                
                current_datetime = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                self.printLog(f"\nGemini 開始串流回應，{current_datetime}...")
                
                # 逐段產生回應文字
                for chunk in response_stream:
                    # print(chunk)
                    # print("-----chunk end-----")
                    if chunk.text:
                        yield chunk.text
                
                current_datetime = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                self.printLog(f"\nGemini 串流已完成，{current_datetime}...")
                return
                
            except (
                exceptions.InternalServerError,
                exceptions.DeadlineExceeded,
                google_exceptions.ResourceExhausted,
            ) as e:
                log_time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                self.printLog(
                    f"[{log_time}]呼叫 API 時發生可重試錯誤 (第 {attempt + 1} 次失敗): {e}",
                    True,
                )
                if attempt < max_retries - 1:
                    if hasattr(e, "retry_delay") and e.retry_delay is not None:
                        print(f" {e.retry_delay}")

                    self.printLog(f"將在 10 秒後重試...", True)
                    time.sleep(10)
                else:
                    self.printLog("[{log_time}]已達到最大重試次數，放棄操作。", True)
                    yield f"呼叫 Google API 失敗，已重試 {max_retries} 次後放棄。最後錯誤：{e}"
                    return
            except Exception as e:
                print("=====發生未知錯誤=====")
                print(e)
                yield f"生成回應時發生未預期的錯誤：{e}"
                return
    @property
    def history(self) -> List:
        """返回目前的對話歷史紀錄。"""
        return self.chat.get_history()
