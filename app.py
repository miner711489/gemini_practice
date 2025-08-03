import os
import shutil
import time
import json
from datetime import datetime
import google.generativeai as genai
from flask import Flask, render_template, request, Response, stream_with_context
from GeminiChatSession import GeminiChatSession
import config

# --- 全域設定 ---
app = Flask(__name__)
RUN_OPTIONS_PATH = "RunOptions.json"
RUN_DIR_PATH = "小說2"
RESPONSE_FILES_DIR = "Response"

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


@app.route('/')
def index():
    """渲染主頁面，顯示所有可用的選項"""
    if not run_options_data:
        return "錯誤：無法載入 RunOptions.json，請檢查檔案是否存在且格式正確。", 500
        
    options = run_options_data.get("options", [])
    return render_template('index.html', options=options)


@app.route('/run', methods=['POST'])
def run_process():
    """處理來自前端的請求，並開始執行 Gemini 任務"""
    run_id = request.form.get('run_id')

    if not run_id:
        return "錯誤：未提供 run_id。", 400

    if not run_options_data:
        return "錯誤：伺服器無法載入設定檔。", 500

    selected_option = next((opt for opt in run_options_data["options"] if opt.get("id") == run_id), None)
    if not selected_option:
        return f"錯誤：在 {RUN_OPTIONS_PATH} 中找不到 ID 為 '{run_id}' 的選項。", 404

    # 使用 stream_with_context 來串流回應
    return Response(stream_with_context(gemini_task_generator(selected_option)), mimetype='text/event-stream')


def gemini_task_generator(json_data):
    """
    這是一個生成器函式，它執行主要的任務邏輯，
    並使用 'yield' 將進度訊息即時傳送到前端。
    """
    def stream_log(message_type, content, showlog = True):
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

        files_to_upload = [os.path.join(RUN_DIR_PATH, dir_name, f) for f in uploader_files]
        files_to_prompt = [os.path.join(RUN_DIR_PATH, dir_name, f) for f in prompt_files]

        yield stream_log("status", f"找到 {len(files_to_upload)} 個待上傳檔案和 {len(files_to_prompt)} 個指令檔。")

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
            yield stream_log("status", f"正在處理第 {i+1}/{total_prompts} 個指令: {os.path.basename(prompt_file)}")
            
            try:
                with open(prompt_file, "r", encoding="utf-8") as f:
                    prompt_content = f.read().strip()
            except FileNotFoundError:
                yield stream_log("error", f"錯誤：找不到指令檔 {prompt_file}")
                continue

            yield stream_log("status", "正在發送訊息至 Gemini...")
            response = chat_session.send_message(prompt=prompt_content, uploaded_files=uploaded_files_result)
            
            yield stream_log("data", response,False) # 將單次回應即時傳到前端
            full_response_content += response + "\n\n====================回應分隔線====================\n\n"

            if i < total_prompts - 1 and (i + 1) % 2 == 0:
                yield stream_log("status", "處理完畢，依據規則暫停 60 秒...")
                time.sleep(60)
                yield stream_log("status", "暫停結束，繼續處理下一個指令。")

        # --- 5. 儲存最終結果 ---
        yield stream_log("status", "所有指令處理完畢，正在儲存最終結果...")
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        response_filename = f"response_{now_str}.txt"
        final_path = os.path.join(RUN_DIR_PATH, dir_name, RESPONSE_FILES_DIR, response_filename)
        
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


if __name__ == '__main__':
    if not run_options_data:
        print("無法啟動伺服器，因為 RunOptions.json 載入失敗。")
    else:
        # debug=True 讓您在修改程式碼後不用重啟伺服器
        app.run(host='0.0.0.0', port=5001, debug=True)
