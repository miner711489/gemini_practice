import os
import re
import shutil
import time
from dotenv import load_dotenv
import config
from datetime import datetime
import xml.etree.ElementTree as ET
import google.generativeai as genai
from google.api_core import exceptions
from GeminiChatSession import GeminiChatSession


# --- 檔案名稱設定 ---
CONFIG_PATH = "config.xml"
# 要上傳的檔案清單
FILE_LIST_PATH = "updateFile.txt"
# 要執行的prompt清單
PROMPT_PATH = "promptList.txt"
# 要儲存回應的檔案
RESPONSE_PATH = "response.txt"

# 要執行的資料夾名稱
Run_Dir_PATH = "小說"
# 存放要上傳檔案資料夾名稱
UploadFiles_Dir = "UploadFiles"
# 存放要問Gmeini的Prompt檔的資料夾名稱
PromptFiles_Dir = "Prompts"
# 存放每次問Gmeini的reponse的資料夾名稱
ResponseFiles_Dir = "Response"

env_filename = ".env"


def read_UploaderFile_list(path):
    read_file_list = ["test.txt"]
    """從指定路徑讀取檔案清單。"""
    print(f"\n正在從 {path} 讀取要上傳的檔案清單...")
    uploader_Files = []
    for filename in os.listdir(path):
        uploader_Files.append(os.path.join(path, filename))

    print("讀取完畢...")
    return uploader_Files


def read_PromptFile_list(path):
    read_file_list = []
    """從指定目錄讀取符合 Prompt數字.txt 格式的檔案，並依數字排序。"""
    print(f"\n正在從 {path} 讀取 Prompt 檔案清單...")
    prompt_files = []
    pattern = re.compile(r"^prompt(\d+)\.txt$")

    # 遍歷目錄
    for filename in os.listdir(path):
        match = pattern.match(filename)
        if match:
            # 取出數字作為排序依據
            num = int(match.group(1))
            prompt_files.append((num, filename))

    # 依數字排序
    prompt_files.sort(key=lambda x: x[0])

    # 只回傳檔名清單（或可加完整路徑）
    sorted_filenames = [os.path.join(path, filename) for _, filename in prompt_files]
    print(f"  - 找到 {len(sorted_filenames)} 個 Prompt 檔案。")
    return sorted_filenames


def read_prompt(path):
    """從指定路徑讀取 prompt 內容。"""
    # print(f"\n正在從 {path} 讀取您的問題...")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"  - 錯誤：找不到指令檔 {path}")
        return None


def save_response(content, path, mode="w"):
    """將回應內容儲存到指定檔案。"""
    try:
        with open(path, mode, encoding="utf-8") as f:
            f.write(content)
        # print("  - 儲存成功！")
    except IOError as e:
        print(f"  - 儲存檔案時發生錯誤：{e}")


def main(prompt_files, uploaded_files):
    # 1. 首先，建立一個對話 Session 的實例
    #   這個實例在整個對話中只需要建立一次。
    generation_config = genai.types.GenerationConfig(
        temperature=2,
        # 其他您需要的設定...
    )

    chat_session = GeminiChatSession(
        model_name=config.MODEL_NAME, generation_config=generation_config
    )

    # 上傳檔案到google Gemini AI Studio
    uploaded_files = chat_session.upload_files(uploaded_files)

    # 清空
    save_response("", RESPONSE_PATH)

    # 讀取 files_to_prompt 裡面的內容並且 print 出來
    start_time = time.perf_counter()
    cnt = 0
    for prompt_file in prompt_files:
        prompt_content = read_prompt(prompt_file)
        # print(f"\n--- {prompt_file} ---\n{prompt_content}\n")
        response = chat_session.send_message(
            prompt=prompt_content, uploaded_files=uploaded_files
        )
        # print(f"Gemini: {response}")
        print(f"\n正在將回應儲存至 {RESPONSE_PATH}...")
        save_response(response, RESPONSE_PATH, "a")
        save_response(
            "\n\n====================回應分隔線====================\n\n",
            RESPONSE_PATH,
            "a",
        )
        cnt = cnt + 1
        if prompt_file != prompt_files[-1]:
            # 暫停 60 秒，避免token爆掉
            # print("程式即將暫停 60 秒...")
            if cnt % 2 == 0:
                print(f"\n暫停 60 秒...")
                time.sleep(60)

    # 計算時間差
    end_time = time.perf_counter()
    execution_time = end_time - start_time
    print(f"\n執行時間共{execution_time:.2f}秒...")

    # 取得當下時間字串
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")  # 例如 20250728_145051
    # 組合資料夾名稱
    copy_response_path = os.path.join(
        Run_Dir_PATH, ResponseFiles_Dir, f"response_{now_str}.txt"
    )
    # 建立資料夾
    os.makedirs(os.path.dirname(copy_response_path), exist_ok=True)

    src = RESPONSE_PATH
    dst = copy_response_path
    shutil.copy2(src, dst)  # 複製檔案（包含內容、權限、metadata）
    print(f"已產生response_{now_str}.txt...")

    # 4. (可選) 隨時可以檢查完整的對話歷史
    if False:
        print("\n--- 對話歷史紀錄 ---")
        for message in chat_session.history:
            # message.parts[0] 可能包含 text 或 file_data
            text_part = (
                message.parts[0].text if hasattr(message.parts[0], "text") else "[檔案]"
            )
            print(f"\n[{message.role.capitalize()}]: {text_part}\n")


# --- 主執行流程 ---
if __name__ == "__main__":

    try:
        API_KEY = config.GOOGLE_API_KEY
        genai.configure(api_key=API_KEY)
        print("API 金鑰設定成功。")
    except Exception as e:
        print(f"設定 API 金鑰時發生錯誤：{e}")
        exit()

    files_to_upload = read_UploaderFile_list(
        os.path.join(Run_Dir_PATH, UploadFiles_Dir)
    )
    files_to_prompt = read_PromptFile_list(os.path.join(Run_Dir_PATH, PromptFiles_Dir))

    if not files_to_upload and not files_to_prompt:
        print("\n檔案清單或指令檔為空或讀取失敗，程式終止。")
        exit()

    # 開始執行上傳行為
    main(files_to_prompt, files_to_upload)
