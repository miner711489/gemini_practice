import os
import shutil
import base64
import time
import json
from datetime import datetime
from flask import (
    Flask,
    render_template,
    request,
    Response,
    stream_with_context,
    jsonify,
)
from GeminiChatSession import GeminiChatSession
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


@app.route("/")
def index():
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

    return render_template("index.html", jsondata=jsondata)


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
        jsondata = []

    return render_template("detail.html", jsondata=jsondata)


@app.route("/history")
def history():
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

    return render_template("history.html", jsondata=jsonarray, id=id)


@app.route("/getHistoryData", methods=["POST"])
def getHistoryData():
    id = request.get_json().get("id")

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
    if not jsonarray:
        jsondata = []
    else:
        jsondata = jsonarray[0]

    dir = jsondata["dir"]

    history_path = os.path.join(
        RUN_DIR_PATH_three,
        dir,
        RESPONSE_FILES_DIR,
    )
    # 取得該資料夾下所有 txt 檔案
    txt_files = []
    if os.path.exists(history_path):
        for fname in os.listdir(history_path):
            if fname.lower().endswith(".txt"):
                txt_files.append({"filename": fname})

    return (jsonify(txt_files), 200)


@app.route("/getTxtContent", methods=["POST"])
def getTxtContent():
    id = request.get_json().get("id")
    filename = request.get_json().get("filename")

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
    if not jsonarray:
        jsondata = []
    else:
        jsondata = jsonarray[0]

    dir = jsondata["dir"]

    txt_file = os.path.join(RUN_DIR_PATH_three, dir, RESPONSE_FILES_DIR, filename)
    if not os.path.exists(txt_file):
        return jsonify({"error": "檔案不存在"}), 404

    try:
        with open(txt_file, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return jsonify({"error": f"讀取檔案時發生錯誤: {e}"}), 500

    return (jsonify({"content": content}), 200)


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
def doSave():
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
    if dir:
        for item in data["prompts"]:
            if item["type"] == "file" and item["mode"] == "n":
                dest_folder = os.path.join(os.getcwd(), RUN_DIR_PATH_three, dir)
                # 檢查資料夾是否存在，如果不存在則創建
                if not os.path.exists(dest_folder):
                    os.makedirs(dest_folder)

                filename = item["content"]
                src_file_path = os.path.join(app.config["TEMP_FOLDER"], filename)
                dest_file_path = os.path.join(dest_folder, filename)

                # 檢查來源檔案是否存在
                if os.path.exists(src_file_path):
                    try:
                        # 使用 shutil.move 來移動檔案
                        shutil.move(src_file_path, dest_file_path)
                        print(f"檔案已成功從 {src_file_path} 移動到 {dest_file_path}")
                        item["mode"] == ""
                    except shutil.Error as e:
                        print(f"移動檔案時發生錯誤: {e}")
                    except Exception as e:
                        print(f"發生意外錯誤: {e}")
                else:
                    print(f"錯誤: 來源檔案不存在於 {src_file_path}")

    id = data["id"]
    if not id == "":
        for item in jsonarray:
            if item["id"] == id:
                item["name"] = data["name"]
                item["dir"] = data["dir"]
                item["prompts"] = data["prompts"]
    else:
        all_ids = [int(item["id"]) for item in jsonarray]
        # 使用 max() 函式找出最大的 id
        max_id = max(all_ids)
        # print(f"jsonarray 中最大的 ID 是: {max_id}")
        new_item = {}
        new_item["id"] = str(max_id + 1)
        new_item["name"] = data["name"]
        new_item["dir"] = data["dir"]
        new_item["prompts"] = data["prompts"]
        jsonarray.append(new_item)

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


@app.route("/runbyid", methods=["POST"])
def runbyid():
    # 使用 stream_with_context 來串流回應
    return Response(
        stream_with_context(gemini_task_generator(request.get_json())),
        mimetype="text/event-stream",
    )


def gemini_task_generator(request_data):

    run_id = request_data.get("id")
    run_model = request_data.get("model")
    token = request_data.get("token")

    def stream_log(message_type, content, showlog=True):
        """輔助函式，用於格式化並傳送串流訊息"""
        log_entry = json.dumps(
            {"type": message_type, "content": content, "token": token}
        )
        if showlog:
            print(content)
        return f"data: {log_entry}\n\n"

    # # <-- 新增：檢查並設定 API Key -->
    # api_key = request_data.get("apiKey")  # <-- 新增：從請求中獲取 API Key
    # if not api_key:
    #     yield stream_log("error", "錯誤：請求中未提供 API Key。")
    #     return  # 停止執行

    # try:
    #     # 設定 Google AI 的 API Key
    #     genai.configure(api_key=api_key)
    #     yield stream_log("status", "API Key 已成功設定。")
    # except Exception as e:
    #     yield stream_log("error", f"設定 API Key 時發生錯誤：{e}")
    #     return  # 停止執行
    # # <-- 新增結束 -->

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
        yield stream_log("status", f"處理程序開始，使用模型{run_model}...")

        # generation_config = genai.types.GenerationConfig(
        #     temperature=2,
        # )

        chat_session = GeminiChatSession(
            model_name=run_model
        )

        uploaded_files_result = []
        run_cnt = 0
        full_response_content = ""
        for item in json_data["prompts"]:
            if "isSend" in item:
                isSend = item["isSend"]
            else:
                isSend = True  # 設定預設值

            if isSend == False:
                continue

            prompt_content = item["content"]
            type = item["type"]

            if type == "file":
                # 判斷是檔案，上傳檔案，並寫到uploaded_files_result裡面
                files_to_upload = [
                    os.path.join(RUN_DIR_PATH_three, dir_name, prompt_content)
                ]
                yield stream_log("status", f"正在上傳檔案: {prompt_content}...")
                lst_upload_files = chat_session.upload_files(files_to_upload)

                if lst_upload_files and len(lst_upload_files) > 0:
                    file_info = lst_upload_files[0]
                    uploaded_files_result.append(file_info)
                    yield stream_log("status", "檔案上傳完成！")
                else:
                    yield stream_log("status", f"檔案上傳失敗或回傳為空，已跳過檔案: {prompt_content}")
            else:
                # 判斷是文字，送出執行
                yield stream_log("status", "正在發送訊息至 Gemini...")
                response = chat_session.send_message(
                    prompt=prompt_content, uploaded_files=uploaded_files_result
                )

                if(response == None):
                    yield stream_log("status", f"發生Response None錯誤，停止執行。")
                    break

                response = response.replace("**","")
                yield stream_log("data", response, False)  # 將單次回應即時傳到前端

                errorResult = (
                    "PROHIBITED_CONTENT" in response
                    or "GenerateRequestsPerMinutePerProjectPerModel" in response
                    or "GenerateRequestsPerDayPerProjectPerModel" in response
                )

                if errorResult:
                    yield stream_log("status", f"發生錯誤，停止執行。")
                    break

                full_response_content += (
                    response
                    + "\n\n====================回應分隔線====================\n\n"
                )
                run_cnt = run_cnt + 1

                if not item == json_data["prompts"][-1]:
                    yield stream_log("status", "處理完畢，暫停 10 秒...")
                    time.sleep(10)
                    yield stream_log("status", "暫停結束，繼續處理下一個指令。")

        if run_cnt > 0 and not full_response_content.strip() == "":
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

            history_filename = f"history_{now_str}.txt"
            history_path = os.path.join(
                RUN_DIR_PATH_three, dir_name, "history", history_filename
            )

            history_to_save = []
            for message in chat_session.history:
                message_dict = {"role": message.role, "parts": []}
                for part in message.parts:
                    # 檢查是否為 TextPart
                    if str(part.text)!="":
                        message_dict["parts"].append(
                            {"type": "text", "text": part.text}
                        )
                    elif str(part.file_data) != "":
                        # FileDataPart 包含 mime_type 和 uri
                        message_dict["parts"].append(
                            {
                                "type": "file_data",
                                "mime_type": part.file_data.mime_type,
                                "uri": part.file_data.file_uri,
                            }
                        )
                    # 如果還有其他類型的 Part (例如 BlobPart)，可以添加處理邏輯。
                    # 但對於 BlobPart (原始位元組數據)，直接保存到 JSON 會導致文件過大，
                    # 且通常不適合重新載入以繼續對話，除非你將原始檔案也保存並重新載入。
                    # 對於需要持久化的檔案，通常建議使用 genai.upload_file 獲取 URI。
                    else:
                        print(f"警告：發現未知類型的對話部分，已跳過：{type(part)}")
                        # 你可以選擇保存一個未知類型的標記或其字串表示
                        # message_dict["parts"].append({"type": "unknown", "content": str(part)})

                history_to_save.append(message_dict)

            os.makedirs(os.path.dirname(history_path), exist_ok=True)
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(history_to_save, f, ensure_ascii=False, indent=4)

            yield stream_log("status", f"對話已成功儲存至: {history_path}")

        else:
            yield stream_log("status", f"發生錯誤，不執行儲存作業。")

        end_time = time.perf_counter()
        execution_time = end_time - start_time
        yield stream_log("done", f"所有任務完成！總執行時間: {execution_time:.2f} 秒。")
    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        yield stream_log("error", f"執行過程中發生未預期的錯誤: {e}\n{error_details}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
