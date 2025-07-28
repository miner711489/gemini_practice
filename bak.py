import os
import xml.etree.ElementTree as ET
import google.generativeai as genai
from google.api_core import exceptions
from GeminiChatSession import GeminiChatSession


# --- 檔案名稱設定 ---
CONFIG_PATH = "config.xml"
# 要執行的資料夾名稱
Run_Dir_PATH = "example"
# 要上傳的檔案清單
FILE_LIST_PATH = "updateFile.txt"
# 要執行的prompt清單
PROMPT_PATH = "promptList.txt"
# 要儲存回應的檔案
RESPONSE_PATH = "response.txt"

def get_response_from_gemini(prompt, uploaded_files, model_name, generation_config):
    """將 prompt、檔案和生成設定傳送給 Gemini 模型並取得回應。"""
    if not uploaded_files:
        return "錯誤：沒有成功上傳的檔案，無法繼續。"

    model = genai.GenerativeModel(model_name=model_name)
    request_content = [prompt] + uploaded_files

    print(
        f"\n正在使用模型 '{model_name}' (Temperature: {generation_config.temperature}) 向 Gemini 發送請求..."
    )
    try:
        response = model.generate_content(
            request_content, generation_config=generation_config
        )
        return response.text
    except exceptions.GoogleAPICallError as e:
        return f"呼叫 Google API 時發生錯誤：{e}"
    except Exception as e:
        return f"生成回應時發生未預期的錯誤：{e}"


def upload_files_to_gemini(file_paths):
    """接收檔案路徑列表，上傳到 Gemini，並返回檔案物件列表。"""
    uploaded_files = []
    print("\n開始上傳檔案...")
    for file_path in file_paths:
        try:
            print(f"  - 上傳中：{file_path}")
            file_obj = genai.upload_file(path=file_path)
            uploaded_files.append(file_obj)
            print(f"  - 成功：{file_obj.display_name} (URI: {file_obj.uri})")
        except FileNotFoundError:
            print(f"  - 錯誤：找不到檔案 {file_path}")
        except Exception as e:
            print(f"  - 上傳檔案 {file_path} 時發生未預期的錯誤：{e}")
    return uploaded_files


def main1():
    ## 邏輯：先上傳檔案到Google的Server，在附上相關的檔案資訊讓他抓已經上傳的檔案
    gemini_files = upload_files_to_gemini(files_to_upload)
    if gemini_files:
        generation_config = genai.types.GenerationConfig(
            temperature=config["temperature"]
        )
        user_prompt = ""
        final_response = get_response_from_gemini(
            user_prompt, gemini_files, config["model_name"], generation_config
        )
    else:
        final_response = "由於所有檔案都上傳失敗，無法生成回應。"
        print("\n" + final_response)

    print("\n===== Gemini 的回應 =====")
    print(final_response)
    print("==========================")
    save_response(final_response, RESPONSE_PATH)
