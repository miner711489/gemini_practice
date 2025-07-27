import os
import xml.etree.ElementTree as ET
import google.generativeai as genai
from google.api_core import exceptions
from GeminiChatSession import GeminiChatSession


# --- 檔案名稱設定 ---
CONFIG_PATH = "config.xml"
FILE_LIST_PATH = "updateFile.txt"
PROMPT_PATH = "prompt.txt"
RESPONSE_PATH = "response.txt"


# --- 準備範例檔案 (僅為方便初次執行) ---
def create_example_files():
    """建立所有執行所需的範例檔案。"""
    print("\n正在檢查並建立範例檔案...")
    try:
        # 建立 config.xml (已更新 Temperature 說明與預設值)
        if not os.path.exists(CONFIG_PATH):
            config_content = """<config>
    <api_key>YOUR_API_KEY_HERE</api_key>
    <model_name>gemini-1.5-flash</model_name>
    <temperature>0.7</temperature>
</config>
"""
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write(config_content)
            print(f"  - 已建立範例設定檔：{CONFIG_PATH}，請務必填入您的 API 金鑰！")

        # 建立要被上傳的資料檔
        with open("file1.txt", "w", encoding="utf-8") as f:
            f.write("這是一篇關於未來城市的小說草稿。\n主角是一位名叫艾拉的年輕發明家，她住在一個漂浮在雲端的城市『天穹城』。")
        with open("file2.txt", "w", encoding="utf-8") as f:
            f.write("艾拉的好友是一位名叫里歐的歷史學家，他對古老的地面世界充滿好奇。")
        
        # 建立上傳清單檔 (updateFile.txt)
        if not os.path.exists(FILE_LIST_PATH):
            with open(FILE_LIST_PATH, "w", encoding="utf-8") as f:
                f.write("file1.txt\n")
                f.write("file2.txt\n")
            print(f"  - 已建立範例上傳清單：{FILE_LIST_PATH}")

        # 建立 Prompt 指令檔 (prompt.txt)
        if not os.path.exists(PROMPT_PATH):
            prompt_content = "請根據我提供的兩個檔案內容，以一個充滿想像力的說書人語氣，續寫一段約150字的故事，描述艾拉和里歐決定一起探索地面世界的冒險開端。"
            with open(PROMPT_PATH, "w", encoding="utf-8") as f:
                f.write(prompt_content)
            print(f"  - 已建立範例指令檔：{PROMPT_PATH}")

    except IOError as e:
        print(f"建立範例檔案時發生錯誤：{e}")
        exit()


# --- 核心功能 (其餘函式與前一版相同，此處省略以保持簡潔) ---

def load_config_from_xml(path):
    """從 XML 檔案載入設定。"""
    print(f"\n正在從 {path} 讀取設定...")
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        config = {
            "api_key": root.find("api_key").text,
            "model_name": root.find("model_name").text,
            "temperature": float(root.find("temperature").text)
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
            files = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        print(f"  - 預計上傳 {len(files)} 個檔案。")
        return files
    except FileNotFoundError:
        print(f"  - 錯誤：找不到檔案清單 {path}")
        return []

def read_prompt(path):
    """從指定路徑讀取 prompt 內容。"""
    print(f"\n正在從 {path} 讀取您的問題...")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"  - 錯誤：找不到指令檔 {path}")
        return None

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

def get_response_from_gemini(prompt, uploaded_files, model_name, generation_config):
    """將 prompt、檔案和生成設定傳送給 Gemini 模型並取得回應。"""
    if not uploaded_files:
        return "錯誤：沒有成功上傳的檔案，無法繼續。"
    
    model = genai.GenerativeModel(model_name=model_name)
    request_content = [prompt] + uploaded_files

    print(f"\n正在使用模型 '{model_name}' (Temperature: {generation_config.temperature}) 向 Gemini 發送請求...")
    try:
        response = model.generate_content(
            request_content,
            generation_config=generation_config
        )
        return response.text
    except exceptions.GoogleAPICallError as e:
        return f"呼叫 Google API 時發生錯誤：{e}"
    except Exception as e:
        return f"生成回應時發生未預期的錯誤：{e}"

def save_response(content, path, mode= "w"):
    """將回應內容儲存到指定檔案。"""
    print(f"\n正在將回應儲存至 {path}...")
    try:
        with open(path, mode, encoding="utf-8") as f:
            f.write(content)
        print("  - 儲存成功！")
    except IOError as e:
        print(f"  - 儲存檔案時發生錯誤：{e}")


def main1():
    ## 邏輯：先上傳檔案到Google的Server，在附上相關的檔案資訊讓他抓已經上傳的檔案
    gemini_files = upload_files_to_gemini(files_to_upload)
    if gemini_files:
        generation_config = genai.types.GenerationConfig(
            temperature=config["temperature"]
        )
        final_response = get_response_from_gemini(
            user_prompt, 
            gemini_files, 
            config["model_name"], 
            generation_config
        )
    else:
        final_response = "由於所有檔案都上傳失敗，無法生成回應。"
        print("\n" + final_response)
    
    print("\n===== Gemini 的回應 =====")
    print(final_response)
    print("==========================")
    save_response(final_response, RESPONSE_PATH)

def main2(config, prompt, uploaded_files):
    # 1. 首先，建立一個對話 Session 的實例
    #   這個實例在整個對話中只需要建立一次。
    generation_config = genai.types.GenerationConfig(
        temperature=2,
        # 其他您需要的設定...
    )

    chat_session = GeminiChatSession(
        model_name=config["model_name"],
        generation_config=generation_config
    )

    # 上傳檔案到google Gemini AI Studio
    uploaded_files = chat_session.upload_files(uploaded_files)

    save_response('', RESPONSE_PATH)

    # 2. 進行第一輪對話
    prompt1 = prompt
    # print(f"使用者: {prompt1}")
    response1 = chat_session.send_message(prompt=prompt1, uploaded_files=uploaded_files)
    # print(f"Gemini: {response1}")

    save_response(response1, RESPONSE_PATH,"a")


    # 3. 進行第二輪對話
    #    模型會因為 chat_session 保存了歷史紀錄，而記得第一輪的內容。
    prompt2 = """接續之前劇情產生後續
巨龍之血發揮作用，李偉的身體產生巨大變化
身高暴漲到超過210cm，滿身肌肉彷彿體內有用不完的精力，下體的長度達到了驚人的五十釐米。粗度更是突破了二十釐米
陳欣用【魅魔之眼】控制李偉，操縱李偉的行為，並且命令李偉不能射精，直到陳欣許可
陳欣主動使用李偉的身體盡情洩慾
運動到一半，陳欣覺得不夠刺激，命令李偉反過來蹂躪陳欣
李偉發揮超人的力量，狠狠對待陳欣，陳欣到達史無前例的快感，
不知過了多久，陳欣終於命令李偉可以射
李偉噴出超乎常理的精液量，陳欣全數吸收
李偉全身虛脫躺在床上不能動，變回原本身高，身體肌肉盡數萎縮，
陳欣好心餵給李偉一瓶強效精力劑，並用【魅魔之眼】命令李偉忘記今晚的事
吸取精液後的陳欣，感受到體內的洶湧脈動，是快速成長的前兆
回到公寓，晚上身體快速成長，成長帶來痛苦但又另一種的快感
隔天醒來，看成長後的身體，測量數據，發現成長得超乎預期，事先準備的內衣(HH罩杯)都穿不下了
本章結束

身體數據
成長前
陳欣身高:282cm，胸圍162cm(FF罩杯)，腰圍63cm，臀圍142cm，腿長196cm
成長後
陳欣身高:303cm，胸圍171cm(JJ罩杯)，腰圍63cm，臀圍145cm，腿長211cm"""

    prompt2 = prompt2
    # print(f"\n使用者: {prompt2}")
    response2 = chat_session.send_message(prompt=prompt2, uploaded_files=uploaded_files)
    # print(f"Gemini: {response2}")
    
    save_response("\n\n\n接續\n\n\n", RESPONSE_PATH,"a")
    save_response(response2, RESPONSE_PATH,"a")


    if(False):
        # 4. (可選) 隨時可以檢查完整的對話歷史
        print("\n--- 對話歷史紀錄 ---")
        for message in chat_session.history:
            # message.parts[0] 可能包含 text 或 file_data
            text_part = message.parts[0].text if hasattr(message.parts[0], 'text') else '[檔案]'
            print(f"[{message.role.capitalize()}]: {text_part}")


# --- 主執行流程 ---
if __name__ == "__main__":
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

    files_to_upload = read_file_list(FILE_LIST_PATH)
    user_prompt = read_prompt(PROMPT_PATH)

    if not files_to_upload or not user_prompt:
        print("\n檔案清單或指令檔為空或讀取失敗，程式終止。")
        exit()
    # print(f"  - 您的問題：\n---\n{user_prompt}\n---")

    # 開始執行上傳行為
    # main1()

    main2(config,user_prompt,files_to_upload)

   
