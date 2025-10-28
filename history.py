from flask import Blueprint, request, render_template, render_template_string
import requests
import os
import json
from datetime import datetime
from flask import jsonify
from config import RESPONSE_FILES_DIR, RUN_DIR_PATH_three


# 創建一個 Blueprint 物件
history_Blueprint = Blueprint("history", __name__)


# 畫面載入
# URL:http://localhost:5000/NTH/
@history_Blueprint.route("/", methods=["GET"])
def PageLoad():
    return "This is NTH PageLoad"


@history_Blueprint.route("/getHistoryData", methods=["POST"])
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
                file_path = os.path.join(history_path, fname)
                creation_time = os.path.getctime(file_path)
                creation_datetime = datetime.fromtimestamp(creation_time)
                txt_files.append(
                    {
                        "filename": fname,
                        "createtime": creation_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

    return (jsonify(txt_files), 200)


# 回傳人事資料
@history_Blueprint.route("/HRData")
def doDeleteFile():

    directory = os.path.join(os.path.dirname(__file__), "templates", "NTH")
    print(directory)
    files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if "gethrinfo" in f and f.endswith(".html")
    ]

    if not files:
        return "No matching files found", 404

    latest_file = max(files, key=os.path.getmtime)
    latest_file_name = os.path.basename(latest_file)
    print(latest_file_name)

    with open(latest_file, "r", encoding="Big5", errors="replace") as f:
        template_content = f.read()

    return render_template_string(template_content)


# 讀取架設在Tomcat的NTH人事資料，用big5編碼回傳
@history_Blueprint.route("/gethrinfo")
def gethrinfo():
    url = "http://localhost:8080/NTH/gethrinfo.html"
    result = requests.get(url)
    result.encoding = "big5"
    return result.text


# 模擬差勤代理人整合介接網址回傳資料
@history_Blueprint.route("/NTHAltUrl", methods=["GET"])
def getNTHAlt():
    UserID = request.args.get("id", "")  # 預設值為空字串
    print(UserID)
    if UserID == "測試":
        return "0"
    else:
        return "0"


@history_Blueprint.route("/filterLog", methods=["GET"])
def filterLog():

    log_file_path = os.path.join(
        os.path.dirname(__file__), "templates", "NTH", "jopnth.log"
    )
    print(log_file_path)

    if not os.path.exists(log_file_path):
        return "Log file not found", 404

    with open(log_file_path, "r", encoding="big5", errors="replace") as f:
        log_content = f.read()
        if "Mail Queue 排程" in log_content:
            print(log_content)

    print("讀取完畢")
