import os
import re
import shutil
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
Run_Dir_PATH = "福利姬"
# 存放要上傳檔案資料夾名稱
UploadFiles_Dir = "UploadFiles"
# 存放要問Gmeini的Prompt檔的資料夾名稱
PromptFiles_Dir = "Prompts"
# 存放每次問Gmeini的reponse的資料夾名稱
ResponseFiles_Dir = "Response"


# --- 準備範例檔案 (僅為方便初次執行) ---
def create_example_files():
    """建立所有執行所需的範例檔案。"""
    print("\n正在檢查並建立範例檔案...")
    try:
        # 建立 config.xml (已更新 Temperature 說明與預設值)
        if not os.path.exists(CONFIG_PATH):
            config_content = """<config>
    <api_key>YOUR_API_KEY_HERE</api_key>
    <model_name>gemini-2.5-flash</model_name>
    <temperature>0.7</temperature>
</config>
"""
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write(config_content)
            print(f"  - 已建立範例設定檔：{CONFIG_PATH}，請務必填入您的 API 金鑰！")

        # 建立 example 資料夾
        if not os.path.exists("example"):
            os.makedirs("example")
            print("  - 已建立 example 資料夾")

        # 建立要被上傳的資料檔到 example 資料夾
        file1_path = os.path.join("example", UploadFiles_Dir, "file1.txt")
        file2_path = os.path.join("example", UploadFiles_Dir, "file2.txt")

        os.makedirs(os.path.dirname(file1_path), exist_ok=True)
        if not os.path.exists(file1_path):
            with open(file1_path, "w", encoding="utf-8") as f:
                f.write("測試內容1。")
        if not os.path.exists(file2_path):
            with open(file2_path, "w", encoding="utf-8") as f:
                f.write("測試內容2。")

        # 建立上傳清單檔 (updateFile.txt)
        # 廢除
        # updateFile_PATH = os.path.join("example", "updateFile.txt")
        # if not os.path.exists(updateFile_PATH):
        #     with open(updateFile_PATH, "w", encoding="utf-8") as f:
        #         f.write("file1.txt\n")
        #         f.write("file2.txt\n")
        #     print(f"  - 已建立範例上傳清單：{updateFile_PATH}")
        # 廢除

        # 建立 Prompt 指令檔 (prompt.txt)
        PROMPT_PATH1 = os.path.join("example", PromptFiles_Dir, "prompt01.txt")
        PROMPT_PATH2 = os.path.join("example", PromptFiles_Dir, "prompt02.txt")
        os.makedirs(os.path.dirname(PROMPT_PATH1), exist_ok=True)
        if not os.path.exists(PROMPT_PATH1):
            prompt_content = "測試指令1，請回復我上傳幾個檔案。"
            with open(PROMPT_PATH1, "w", encoding="utf-8") as f:
                f.write(prompt_content)

        if not os.path.exists(PROMPT_PATH2):
            prompt_content = "測試指令2，請回復我剛剛上傳的檔案內容。"
            with open(PROMPT_PATH2, "w", encoding="utf-8") as f:
                f.write(prompt_content)

        # 廢除
        # 建立執行指令檔清單 (promptList.txt)
        # PROMPT_LIST_PATH = os.path.join("example", "promptList.txt")
        # if not os.path.exists(PROMPT_LIST_PATH):
        #     with open(PROMPT_LIST_PATH, "w", encoding="utf-8") as f:
        #         f.write("prompt1.txt\n")
        #         f.write("prompt2.txt\n")
        #     print(f"  - 已建立執行指令檔清單：{PROMPT_LIST_PATH}")
        # 廢除

    except IOError as e:
        print(f"建立範例檔案時發生錯誤：{e}")
        exit()


# --- 核心功能 ---
def load_config_from_xml(path):
    """從 XML 檔案載入設定。"""
    print(f"\n正在從 {path} 讀取設定...")
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        config = {
            "api_key": root.find("api_key").text,
            "model_name": root.find("model_name").text,
            "temperature": float(root.find("temperature").text),
        }
        if config["api_key"] == "YOUR_API_KEY_HERE":
            print("  - 警告：偵測到預設 API 金鑰，請務必在 config.xml 中更新！")

        print("  - 設定讀取成功。")
        return config
    except FileNotFoundError:
        print(f"  - 錯誤：找不到設定檔 {path}")
        return None
    except (ET.ParseError, AttributeError, ValueError) as e:
        print(f"  - 錯誤：解析 {path} 失敗，請檢查檔案格式是否正確。錯誤訊息：{e}")
        return None


def read_file_list(path):
    """從指定路徑讀取檔案清單。"""
    print(f"\n正在從 {path} 讀取要上傳的檔案清單...")
    try:
        with open(path, "r", encoding="utf-8") as f:
            files = [
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]
        print(f"  - 預計上傳 {len(files)} 個檔案。")
        return files
    except FileNotFoundError:
        print(f"  - 錯誤：找不到檔案清單 {path}")
        return []


def read_UploaderFile_list(path):
    """從指定路徑讀取檔案清單。"""
    print(f"\n正在從 {path} 讀取要上傳的檔案清單...")
    uploader_Files = []
    for filename in os.listdir(path):
        uploader_Files.append(os.path.join(path, filename))

    print("讀取完畢...")
    return uploader_Files


def read_PromptFile_list(path):
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
    print(f"\n正在將回應儲存至 {path}...")
    try:
        with open(path, mode, encoding="utf-8") as f:
            f.write(content)
        print("  - 儲存成功！")
    except IOError as e:
        print(f"  - 儲存檔案時發生錯誤：{e}")


def main(config, prompt_files, uploaded_files):
    # 1. 首先，建立一個對話 Session 的實例
    #   這個實例在整個對話中只需要建立一次。
    generation_config = genai.types.GenerationConfig(
        temperature=2,
        # 其他您需要的設定...
    )

    chat_session = GeminiChatSession(
        model_name=config["model_name"], generation_config=generation_config
    )

    # 上傳檔案到google Gemini AI Studio
    uploaded_files = chat_session.upload_files(uploaded_files)

    # 清空
    save_response("", RESPONSE_PATH)

    # 讀取 files_to_prompt 裡面的內容並且 print 出來
    for prompt_file in prompt_files:
        prompt_content = read_prompt(prompt_file)
        # print(f"\n--- {prompt_file} ---\n{prompt_content}\n")
        response = chat_session.send_message(
            prompt=prompt_content, uploaded_files=uploaded_files
        )
        # print(f"Gemini: {response}")
        save_response(response, RESPONSE_PATH, "a")
        save_response("\n\n\n", RESPONSE_PATH, "a")

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

    # 4. (可選) 隨時可以檢查完整的對話歷史
    print("\n--- 對話歷史紀錄 ---")
    for message in chat_session.history:
        # message.parts[0] 可能包含 text 或 file_data
        text_part = (
            message.parts[0].text if hasattr(message.parts[0], "text") else "[檔案]"
        )
        print(f"\n[{message.role.capitalize()}]: {text_part}\n")


# --- 主執行流程 ---
if __name__ == "__main__":
    # 建立範例檔案
    create_example_files()

    config = load_config_from_xml(CONFIG_PATH)
    if not config:
        exit()

    try:
        genai.configure(api_key=config["api_key"])
        print("API 金鑰設定成功。")
    except Exception as e:
        print(f"設定 API 金鑰時發生錯誤：{e}")
        exit()

    files_to_upload = read_UploaderFile_list(
        os.path.join(Run_Dir_PATH, UploadFiles_Dir)
    )
    files_to_prompt = read_PromptFile_list(os.path.join(Run_Dir_PATH, PromptFiles_Dir))

    if not files_to_upload or not files_to_prompt:
        print("\n檔案清單或指令檔為空或讀取失敗，程式終止。")
        exit()

    # 開始執行上傳行為
    main(config, files_to_prompt, files_to_upload)
