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

    return render_template("history.html", jsondata=jsonarray)

# 傳入ID，回傳先前產生的檔案清單
@history_Blueprint.route("/getHistoryFileList", methods=["POST"])
def getHistoryFileList():
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
    # 按 createtime 由新到舊排序（最新在前）
    try:
        txt_files.sort(key=lambda x: datetime.strptime(x["createtime"], "%Y-%m-%d %H:%M:%S"), reverse=True)
    except Exception as e:
        print(f"排序時發生錯誤: {e}")

    return (jsonify(txt_files), 200)

# 取得之前產生的小說內容
@history_Blueprint.route("/getTxtContent", methods=["POST"])
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

@history_Blueprint.route("/doDeleteFile", methods=["POST"])
def doDeleteFile():
    id = request.get_json().get("id")
    files = request.get_json().get("files")

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

    if os.path.exists(history_path):
        for fname in os.listdir(history_path):
            if fname in files:
                file_path = os.path.join(history_path, fname)
                try:
                    os.remove(file_path)
                    print(f"刪除 {file_path} 成功。")
                except FileNotFoundError:
                    pass
                except Exception as e:
                    print(f"刪除檔案 {file_path} 時發生錯誤: {e}")
                continue

    return (jsonify(""), 200)





