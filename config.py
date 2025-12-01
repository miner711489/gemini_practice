# 共用設定檔 (config.py)
# 把專案中會被多個模組共用的常數放在這裡。
import os
from dotenv import load_dotenv


def setup_and_load_env():
    env_filename = ".env"

    # 步驟 1: 檢查 .env 檔案是否存在
    if not os.path.exists(env_filename):
        print(f"⚠️  '{env_filename}' 檔案不存在，正在為您建立一個新的...")

        # 預設寫入的內容
        default_content = 'GOOGLE_API_KEY="在這裡貼上你的API金鑰"\n'

        try:
            # 步驟 2: 如果不存在，則建立它並寫入模板內容
            with open(env_filename, "w", encoding="utf-8") as f:
                f.write(default_content)

            print(f"✅  成功建立 '{env_filename}' 檔案。")
            print(
                "🛑  請打開該檔案，將您的 Google API 金鑰貼入引號中，然後重新執行程式。"
            )
            exit()

        except IOError as e:
            print(f"❌ 錯誤：無法寫入 '{env_filename}' 檔案。請檢查資料夾權限。")
            print(f"詳細錯誤: {e}")
            exit()  # 發生錯誤，也結束程式

    load_dotenv()

    # 步驟 4: 讀取並驗證 GOOGLE_API_KEY
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "在這裡貼上你的API金鑰":
        print("❌ 未能在 .env 檔案中找到有效的 GOOGLE_API_KEY。")
        print("🛑  請確認您已將金鑰貼入 .env 檔案並儲存後，再重新執行程式。")
        exit()

    return api_key


def get_TEMP_FOLDER():
    dir_path = os.path.join(os.getcwd(), RUN_DIR_PATH_three, "temp")
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return dir_path


# 呼叫函式來完成環境設定並取得 API Key
GOOGLE_API_KEY = setup_and_load_env()
RESPONSE_FILES_DIR = "Response"
RUN_DIR_PATH_three = "小說3"
TEMP_FOLDER = get_TEMP_FOLDER()
