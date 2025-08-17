import os
import shutil
import base64
import time
import json
from datetime import datetime
import google.generativeai as genai
from flask import (
    Flask,
    render_template,
    request,
    Response,
    stream_with_context,
    jsonify,
)
from GeminiChatSession import GeminiChatSession
import config
from collections import defaultdict


# --- 全域設定 ---
app = Flask(__name__)
RUN_OPTIONS_PATH = "RunOptions.json"
RUN_DIR_PATH = "小說2"
RESPONSE_FILES_DIR = "Response"

RUN_DIR_PATH_three = "小說3"
TEMP_FOLDER = os.path.join(os.getcwd(), RUN_DIR_PATH_three, "temp")
# 檢查資料夾是否存在，如果不存在則創建
if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)
app.config["TEMP_FOLDER"] = TEMP_FOLDER


def load_run_options():
    """載入設定檔"""
    try:
        with open(RUN_OPTIONS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"錯誤：找不到設定檔 {RUN_OPTIONS_PATH}")
        return None
    except json.JSONDecodeError:
        print(f"錯誤：{RUN_OPTIONS_PATH} 格式不正確。")
        return None


run_options_data = load_run_options()


@app.route("/")
def index():
    """渲染主頁面，顯示所有可用的選項"""
    if not run_options_data:
        return "錯誤：無法載入 RunOptions.json，請檢查檔案是否存在且格式正確。", 500

    options = run_options_data.get("options", [])

    """載入資料"""
    data_path = "data.json"
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            jsondata = json.load(f)
    except FileNotFoundError:
        print(f"錯誤：找不到設定檔 {data_path}")
        return None
    except json.JSONDecodeError:
        print(f"錯誤：{data_path} 格式不正確。")
        return None

    return render_template("index.html", options=options, jsondata=jsondata)


@app.route("/detail")
def detail():
    id = request.args.get("id")

    """載入資料"""
    data_path = "data.json"
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            jsonarray = json.load(f)
    except FileNotFoundError:
        print(f"錯誤：找不到設定檔 {data_path}")
        return None
    except json.JSONDecodeError:
        print(f"錯誤：{data_path} 格式不正確。")
        return None

    jsonarray = list(filter(lambda item: item["id"] == id, jsonarray))
    if jsonarray:
        jsondata = jsonarray[0]
    else:
        jsondata = {}
        jsondata["name"] = ""

    return render_template("detail.html", jsondata=jsondata)


@app.route("/uploadfile", methods=["POST"])
def uploadfile():
    """
    接收前端發送的 JSON 格式的檔案名稱和 Base64 編碼字串，並將其存為檔案。
    """
    try:
        # 1. 檢查請求是否包含 JSON 資料
        if not request.is_json:
            return jsonify({"error": "請求必須是 JSON 格式"}), 400

        # 2. 取得 JSON 資料
        data = request.get_json()
        file_name = data.get("file")
        base64_string = data.get("base64")

        # 3. 檢查必要的欄位是否存在
        if not file_name or not base64_string:
            return jsonify({"error": "缺少檔案名稱或 Base64 字串"}), 400

        # 4. 解碼 Base64 字串
        try:
            # Base64 解碼
            file_content = base64.b64decode(base64_string)
        except base64.binascii.Error:
            return jsonify({"error": "無效的 Base64 編碼字串"}), 400

        file_path = os.path.join(app.config["TEMP_FOLDER"], file_name)

        # 6. 將二進位內容寫入檔案
        with open(file_path, "wb") as f:
            f.write(file_content)

        print(f"成功將檔案 '{file_name}' 儲存到 '{file_path}'")

        # 7. 回傳成功的回應給前端
        return (
            jsonify(
                {"message": "檔案已成功儲存", "fileName": file_name, "path": file_path}
            ),
            200,
        )

    except Exception as e:
        # 處理任何其他未預期的錯誤
        print(f"處理請求時發生錯誤：{e}")
        return jsonify({"error": "伺服器處理錯誤"}), 500


@app.route("/doSave", methods=["POST"])
def do_save():
    # 檢查請求是否包含 JSON 資料
    if not request.is_json:
        return jsonify({"error": "請求必須是 JSON 格式"}), 400

    # 取得前端發送的 JSON 陣列
    # request.get_json() 會自動將 JSON 陣列解析為 Python 列表
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify({"error": f"解析 JSON 失敗: {e}"}), 400

    """載入資料"""
    data_path = "data.json"
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            jsonarray = json.load(f)
    except FileNotFoundError:
        print(f"錯誤：找不到設定檔 {data_path}")
        return None
    except json.JSONDecodeError:
        print(f"錯誤：{data_path} 格式不正確。")
        return None

    dir = data["dir"]
    for item in data["prompts"]:
        if item["type"] == "file" and item["mode"] == "n":
            dest_folder = os.path.join(os.getcwd(), RUN_DIR_PATH_three, dir)
            # 檢查資料夾是否存在，如果不存在則創建
            if not os.path.exists(dest_folder):
                os.makedirs(dest_folder)

            filename = item["content"]
            src_file_path = os.path.join(app.config["TEMP_FOLDER"], filename)
            dest_file_path = os.path.join(dest_folder, filename)

            print("路徑")
            print(src_file_path)
            print(dest_file_path)

            # 檢查來源檔案是否存在
            if os.path.exists(src_file_path):
                try:
                    # 使用 shutil.move 來移動檔案
                    shutil.move(src_file_path, dest_file_path)
                    print(f"檔案已成功從 {src_file_path} 移動到 {dest_file_path}")
                except shutil.Error as e:
                    print(f"移動檔案時發生錯誤: {e}")
                except Exception as e:
                    print(f"發生意外錯誤: {e}")
            else:
                print(f"錯誤: 來源檔案不存在於 {src_file_path}")

    id = data["id"]
    for item in jsonarray:
        if item["id"] == id:
            item["name"] = data["name"]
            item["dir"] = data["dir"]
            item["prompts"] = data["prompts"]

    try:
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(jsonarray, f, indent=2, ensure_ascii=False)
    except FileNotFoundError:
        print(f"錯誤：找不到設定檔 {data_path}")
        return None
    except json.JSONDecodeError:
        print(f"錯誤：{data_path} 格式不正確。")
        return None

    # 回傳 JSON 回應給前端
    return (jsonify({"message": "檔案已成功儲存"}), 200)


@app.route("/run", methods=["POST"])
def run_process():
    """處理來自前端的請求，並開始執行 Gemini 任務"""
    run_id = request.form.get("run_id")

    if not run_id:
        return "錯誤：未提供 run_id。", 400

    if not run_options_data:
        return "錯誤：伺服器無法載入設定檔。", 500

    selected_option = next(
        (opt for opt in run_options_data["options"] if opt.get("id") == run_id), None
    )
    if not selected_option:
        return f"錯誤：在 {RUN_OPTIONS_PATH} 中找不到 ID 為 '{run_id}' 的選項。", 404

    # 使用 stream_with_context 來串流回應
    return Response(
        stream_with_context(gemini_task_generator(selected_option)),
        mimetype="text/event-stream",
    )


def gemini_task_generator(json_data):
    """
    這是一個生成器函式，它執行主要的任務邏輯，
    並使用 'yield' 將進度訊息即時傳送到前端。
    """

    def stream_log(message_type, content, showlog=True):
        """輔助函式，用於格式化並傳送串流訊息"""
        log_entry = json.dumps({"type": message_type, "content": content})
        if showlog:
            print(content)
        return f"data: {log_entry}\n\n"

    try:
        start_time = time.perf_counter()
        yield stream_log("status", "處理程序開始...")

        # --- 1. 準備檔案路徑 ---
        dir_name = json_data["dir"]
        uploader_files = json_data["uploader_files"]
        prompt_files = json_data["prompt_files"]

        files_to_upload = [
            os.path.join(RUN_DIR_PATH, dir_name, f) for f in uploader_files
        ]
        files_to_prompt = [
            os.path.join(RUN_DIR_PATH, dir_name, f) for f in prompt_files
        ]

        yield stream_log(
            "status",
            f"找到 {len(files_to_upload)} 個待上傳檔案和 {len(files_to_prompt)} 個指令檔。",
        )

        generation_config = genai.types.GenerationConfig(
            temperature=2,
            # 其他您需要的設定...
        )

        chat_session = GeminiChatSession(
            model_name=config.MODEL_NAME, generation_config=generation_config
        )

        # --- 3. 上傳檔案 ---
        if files_to_upload:
            yield stream_log("status", f"正在上傳檔案: {', '.join(uploader_files)}...")
            uploaded_files_result = chat_session.upload_files(files_to_upload)
            yield stream_log("status", "檔案上傳完成！")
        else:
            uploaded_files_result = []
            yield stream_log("status", "沒有需要上傳的檔案。")

        # --- 4. 迭代處理 Prompt ---
        full_response_content = ""
        total_prompts = len(files_to_prompt)
        for i, prompt_file in enumerate(files_to_prompt):
            yield stream_log(
                "status",
                f"正在處理第 {i+1}/{total_prompts} 個指令: {os.path.basename(prompt_file)}",
            )

            try:
                with open(prompt_file, "r", encoding="utf-8") as f:
                    prompt_content = f.read().strip()
            except FileNotFoundError:
                yield stream_log("error", f"錯誤：找不到指令檔 {prompt_file}")
                continue

            yield stream_log("status", "正在發送訊息至 Gemini...")
            response = chat_session.send_message(
                prompt=prompt_content, uploaded_files=uploaded_files_result
            )

            yield stream_log("data", response, False)  # 將單次回應即時傳到前端
            full_response_content += (
                response + "\n\n====================回應分隔線====================\n\n"
            )

            if i < total_prompts - 1 and (i + 1) % 2 == 0:
                yield stream_log("status", "處理完畢，依據規則暫停 60 秒...")
                time.sleep(60)
                yield stream_log("status", "暫停結束，繼續處理下一個指令。")

        # --- 5. 儲存最終結果 ---
        yield stream_log("status", "所有指令處理完畢，正在儲存最終結果...")
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        response_filename = f"response_{now_str}.txt"
        final_path = os.path.join(
            RUN_DIR_PATH, dir_name, RESPONSE_FILES_DIR, response_filename
        )

        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        with open(final_path, "w", encoding="utf-8") as f:
            f.write(full_response_content)

        yield stream_log("status", f"回應已成功儲存至: {final_path}")

        end_time = time.perf_counter()
        execution_time = end_time - start_time
        yield stream_log("done", f"所有任務完成！總執行時間: {execution_time:.2f} 秒。")

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        yield stream_log("error", f"執行過程中發生未預期的錯誤: {e}\n{error_details}")


@app.route("/runbyid", methods=["POST"])
def runbyid():
    """處理來自前端的請求，並開始執行 Gemini 任務"""
    run_id = request.args.get("id")

    # 使用 stream_with_context 來串流回應
    return Response(
        stream_with_context(gemini_task_generator_2(run_id)),
        mimetype="text/event-stream",
    )


def gemini_task_generator_2(run_id):

    def stream_log(message_type, content, showlog=True):
        """輔助函式，用於格式化並傳送串流訊息"""
        log_entry = json.dumps({"type": message_type, "content": content})
        if showlog:
            print(content)
        return f"data: {log_entry}\n\n"

    """載入資料"""
    data_path = "data.json"
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            jsonarray = json.load(f)
    except FileNotFoundError:
        print(f"錯誤：找不到設定檔 {data_path}")
        return None
    except json.JSONDecodeError:
        print(f"錯誤：{data_path} 格式不正確。")
        return None

    jsonarray = list(filter(lambda item: item["id"] == run_id, jsonarray))
    if jsonarray:
        json_data = jsonarray[0]

    dir_name = json_data["dir"]

    try:
        start_time = time.perf_counter()
        yield stream_log("status", "處理程序開始...")

        generation_config = genai.types.GenerationConfig(
            temperature=2,
            # 其他您需要的設定...
        )

        chat_session = GeminiChatSession(
            model_name=config.MODEL_NAME, generation_config=generation_config
        )

        uploaded_files_result = []
        run_cnt = 0
        full_response_content = ""
        for item in json_data["prompts"]:

            prompt_content = item["content"]
            type = item["type"]

            if type == "file":
                # 判斷是檔案，上傳檔案，並寫道uploaded_files_result裡面
                files_to_upload = [os.path.join(RUN_DIR_PATH_three, dir_name, prompt_content)]
                yield stream_log("status", f"正在上傳檔案: {prompt_content}...")
                uploaded_files_result.append(chat_session.upload_files(files_to_upload)[0]) 
                yield stream_log("status", "檔案上傳完成！")
            else:
                run_cnt = run_cnt + 1

                # 判斷是文字，送出執行
                yield stream_log("status", "正在發送訊息至 Gemini...")
                response = chat_session.send_message(
                    prompt=prompt_content, uploaded_files=uploaded_files_result
                )

                yield stream_log("data", response, False)  # 將單次回應即時傳到前端

                full_response_content += (
                    response
                    + "\n\n====================回應分隔線====================\n\n"
                )

                if run_cnt % 2 == 0:
                    yield stream_log("status", "處理完畢，暫停 30 秒...")
                    time.sleep(30)
                    yield stream_log("status", "暫停結束，繼續處理下一個指令。")

        # --- 5. 儲存最終結果 ---
        yield stream_log("status", "所有指令處理完畢，正在儲存最終結果...")
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        response_filename = f"response_{now_str}.txt"
        final_path = os.path.join(
            RUN_DIR_PATH_three, dir_name, RESPONSE_FILES_DIR, response_filename
        )

        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        with open(final_path, "w", encoding="utf-8") as f:
            f.write(full_response_content)

        yield stream_log("status", f"回應已成功儲存至: {final_path}")

        end_time = time.perf_counter()
        execution_time = end_time - start_time
        yield stream_log("done", f"所有任務完成！總執行時間: {execution_time:.2f} 秒。")
    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        yield stream_log("error", f"執行過程中發生未預期的錯誤: {e}\n{error_details}")


if __name__ == "__main__":
    if not run_options_data:
        print("無法啟動伺服器，因為 RunOptions.json 載入失敗。")
    else:
        # debug=True 讓您在修改程式碼後不用重啟伺服器
        app.run(host="0.0.0.0", port=5001, debug=True)
