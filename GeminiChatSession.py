import os
import time
import random
from datetime import datetime
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

    def printLog(self, obj: Any, mustShow: bool = False):
        showLog = False
        if mustShow or showLog:
            print(obj)

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

        system_instruction_text = """小說產生原則
沒有字數限制，但是要在保證文章品質的情況下盡可能的輸出更多文字與延長篇幅，你需要寫得非常詳細，且避免重複和無聊内容。
盡可能的像人與人之間的對話，包含對話和聲音描寫，描寫心理變化和感受，使用通俗易懂的語言，且要有一定對話內容與連續性。
角色之間的互動更具臨場感。若角色之間有衝突或情感波動，務必鋪陳心理變化與反應過程，讓讀者能感受到角色內心的拉扯與真實性。
避免過度文藝化表達，使用直白具體的描述方式，甚至允許部分粗俗描述方式。
場景要夠震撼，多細節才能顯得真實，給人身臨其境的感受。
故事要符合邏輯。所有內容融為一體,不分點輸出,但可以分段，不要自作主張地分章節，我需要連續的文章，上下的對話可以貫通的那種。
我需要你始終用繁體中文與我對話
        """

        # if api_key:
        #     genai.configure(api_key=api_key)

        self.printLog(f"正在初始化模型 '{model_name}'...")
        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction_text,
            safety_settings=None,  # 如果需要安全設置，可以在這裡配置
        )
        self.generation_config = generation_config
        # 使用 model.start_chat() 來建立一個具有狀態的對話物件
        self.chat = self.model.start_chat(history=initial_history or [])
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
        processing_files = []  # 用於存放已上傳但仍在處理中的檔案
        jump = False
        for path in file_paths:
            try:
                NeedUpdate = True

                # 找找看之前上傳的檔案能不能用
                update_file_name = os.path.basename(path)
                print(f"update_file_name: {update_file_name}")
                all_files = genai.list_files()
                matching_files = [
                    f for f in all_files if f.display_name == update_file_name
                ]
                if matching_files:
                    matching_files.sort(key=lambda f: f.create_time, reverse=True)
                    if matching_files[0].state.name == "ACTIVE":
                        print(f"抓到先前上傳的")
                        print(matching_files[0])
                        processing_files.append(matching_files[0])
                        NeedUpdate = False
                        jump = True

                if NeedUpdate:
                    print(f"正在上傳檔案：{path}")
                    # 假設 genai 有 upload_file 方法，實際請依官方 API 調整
                    file_obj = genai.upload_file(
                        path, display_name=os.path.basename(path)
                    )
                    # uploaded_files.append(file_obj)
                    processing_files.append(file_obj)
                    # print(f"檔案上傳成功：{path}")
            except Exception as e:
                print(f"檔案上傳失敗：{path}，錯誤：{e}")

        print("\n--- 所有檔案上傳請求已提交，開始等待後端處理 ---")

        request_delay = 5
        while processing_files:
            print(
                f"\n還有 {len(processing_files)} 個檔案正在處理中... ({request_delay}秒後檢查)"
            )
            if not jump:
                time.sleep(request_delay)

            # 為了能在迴圈中安全地移除元素，我們遍歷列表的副本
            # 或者建立一個新的列表來存放下一輪還需要處理的檔案
            still_processing = []
            for file_obj in processing_files:
                try:
                    # 獲取檔案的最新狀態
                    latest_file_state = genai.get_file(name=file_obj.name)

                    if latest_file_state.state.name == "ACTIVE":
                        print(
                            f"✅ 成功：'{latest_file_state.display_name}' 已準備就緒 (ACTIVE)。"
                        )
                        uploaded_files.append(latest_file_state)
                    elif latest_file_state.state.name == "FAILED":
                        print(
                            f"❌ 失敗：'{latest_file_state.display_name}' 處理失敗 (FAILED)。"
                        )
                        uploaded_files.append(
                            {
                                "path": latest_file_state.display_name,
                                "error": "File processing failed.",
                            }
                        )
                    else:  # 仍然是 PROCESSING
                        # 將仍在處理的檔案放回下一輪的檢查清單
                        still_processing.append(file_obj)

                except Exception as e:
                    print(
                        f"❌ 錯誤：檢查 '{file_obj.display_name}' 狀態時發生錯誤: {e}"
                    )
                    # failed_files.append({"path": file_obj.display_name, "error": f"Error checking status: {e}"})

                processing_files = still_processing

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
        base_delay = 2  # 基礎延遲時間（秒）

        for attempt in range(max_retries):
            current_datetime = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            self.printLog(f"\n正在向 Gemini 傳送訊息，{current_datetime}...")
            try:
                # 對於多輪對話，我們使用 chat.send_message() 而非 model.generate_content()
                response = self.chat.send_message(
                    request_content,
                    generation_config=self.generation_config,
                    # ,safety_settings
                )
                current_datetime = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                self.printLog(f"\nGemini 已回傳訊息，{current_datetime}...")
                return response.text
            except (exceptions.InternalServerError, exceptions.DeadlineExceeded) as e:
                self.printLog(
                    f"呼叫 API 時發生可重試錯誤 (第 {attempt + 1} 次失敗): {e}", True
                )
                if attempt < max_retries - 1:
                    # 指數退避邏輯：等待時間 = 基礎延遲 * 2^嘗試次數 + 一個隨機的毫秒數
                    wait_time = (base_delay**attempt) + random.uniform(0, 1)
                    self.printLog(f"將在 {wait_time:.2f} 秒後重試...", True)
                    time.sleep(wait_time)
                else:
                    self.printLog("已達到最大重試次數，放棄操作。", True)
                    return f"呼叫 Google API 失敗，已重試 {max_retries} 次後放棄。最後錯誤：{e}"
            except Exception as e:
                return f"生成回應時發生未預期的錯誤：{e}"

    @property
    def history(self) -> List:
        """返回目前的對話歷史紀錄。"""
        return self.chat.history
