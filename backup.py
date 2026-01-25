from flask import Blueprint, request, render_template, render_template_string
from flask import jsonify
from flask import Flask, redirect, url_for, session
import requests
import os
import json
from datetime import datetime
from config import Google_AI_STUDIO_BACKUP_DIR
import os
import io
import json
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaIoBaseDownload

# 加入這行來允許 HTTP 連線 (僅限開發環境使用)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# 創建一個 Blueprint 物件
backup_Blueprint = Blueprint("backup", __name__)

CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]

# --- HTML 樣板 ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Google AI Studio 備份工具</title></head>
<body>
    <h1>Google AI Studio 紀錄備份</h1>
    {% if not logged_in %}
        <a href="/backup/login">登入 Google 帳號</a>
    {% else %}
        <h3>檔案列表 (來自 'Google AI Studio' 資料夾)</h3>
        <table border="1">
            <tr><th>檔名</th><th>ID</th><th>操作</th></tr>
            {% for file in files %}
            <tr>
                <td>{{ file['name'] }}</td>
                <td>{{ file['id'] }}</td>
                <td><a href="/copy/{{ file['id'] }}?name={{ file['name'] }}">備份到備份資料夾</a></td>
            </tr>
            {% endfor %}
        </table>
        <p><a href="/logout">登出</a></p>
    {% endif %}
    {% if message %}<p><strong>{{ message }}</strong></p>{% endif %}
</body>
</html>
"""


# 畫面載入
@backup_Blueprint.route("/", methods=["GET"])
def PageLoad():

    useAIpage = False

    if not useAIpage:
        file_path = os.path.join(Google_AI_STUDIO_BACKUP_DIR)
        lst_File_dir = os.listdir(file_path)

        return render_template("backup.html", lstFile=lst_File_dir)
    else:
        message = request.args.get("message")
        if "credentials" not in session:
            return render_template_string(HTML_TEMPLATE, logged_in=False)

        service = get_drive_service()
        # 尋找 Google AI Studio 資料夾 (預設通常叫 'Google AI Studio')
        results = (
            service.files()
            .list(
                q="name = 'Google AI Studio' and mimeType = 'application/vnd.google-apps.folder'",
                fields="files(id)",
            )
            .execute()
        )
        folders = results.get("files", [])

        if not folders:
            return render_template_string(
                HTML_TEMPLATE, logged_in=True, message="找不到 Google AI Studio 資料夾"
            )

        folder_id = folders[0]["id"]
        # 列出該資料夾下的所有檔案
        file_results = (
            service.files()
            .list(q=f"'{folder_id}' in parents", fields="files(id, name)")
            .execute()
        )
        files = file_results.get("files", [])
        return render_template_string(
            HTML_TEMPLATE, logged_in=True, files=files, message=message
        )


def get_drive_service():
    if "credentials" not in session:
        return None
    creds = Credentials(**session["credentials"])
    return build("drive", "v3", credentials=creds)


@backup_Blueprint.route("/login")
def login():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
    flow.redirect_uri = url_for("backup.callback", _external=True)
    authorization_url, state = flow.authorization_url()
    print(authorization_url)

    session["state"] = state
    return redirect(authorization_url)


"""
取得Google Drive上，Google AI Studio資料夾的prompt檔案清單
"""


@backup_Blueprint.route("/getDriveFiles")
def getDriveFiles():

    if "credentials" not in session:
        pass
    else:
        service = get_drive_service()
        results = (
            service.files()
            .list(
                q="name = 'Google AI Studio' and mimeType = 'application/vnd.google-apps.folder'",
                fields="files(id)",
            )
            .execute()
        )
        folders = results.get("files", [])

        if not folders:
            return render_template_string(
                HTML_TEMPLATE, logged_in=True, message="找不到 Google AI Studio 資料夾"
            )

        folder_id = folders[0]["id"]
        #'mimeType': 'application/vnd.google-makersuite.prompt'
        # 列出該資料夾下的所有檔案
        file_results = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and mimeType = 'application/vnd.google-makersuite.prompt'",
                fields="files(id, name)",
            )
            .execute()
        )
        files = file_results.get("files", [])

    return (jsonify(files), 200)


# 讀取雲端硬碟上的檔案內容，顯示到網頁上
@backup_Blueprint.route("/doReadDriveFile", methods=["POST"])
def doReadDriveFile():
    GoogleDriveFileId = request.get_json().get("GoogleDriveFileId")

    if not GoogleDriveFileId:
        return (jsonify({"error": "Missing GoogleDriveFileId"}), 200)

    if "credentials" not in session:
        return (jsonify({"error": "NO GoogleDrive authenticated"}), 200)

    try:
        GoogleDriveFileContent = getGoogleDriveFileContent(GoogleDriveFileId)
    except Exception as e:
        return (jsonify({"error": str(e)}), 200)

    try:
        content = doPraseFileContent(GoogleDriveFileContent)
    except json.JSONDecodeError:
        return (jsonify({"error": str(e)}), 200)

    return (
        jsonify({"content": content}),
        200,
    )


# 下載到本機，同時顯示到網頁上
@backup_Blueprint.route("/doDownload", methods=["POST"])
def doDownload():
    GoogleDriveFileId = request.get_json().get("GoogleDriveFileId")
    GoogleDriveFileNam = request.get_json().get("GoogleDriveFileNam")

    if not GoogleDriveFileId:
        return (jsonify({"error": "Missing GoogleDriveFileId"}), 200)

    if "credentials" not in session:
        return (jsonify({"error": "NO GoogleDrive authenticated"}), 200)

    try:
        GoogleDriveFileContent = getGoogleDriveFileContent(GoogleDriveFileId)
    except Exception as e:
        return (jsonify({"error": str(e)}), 200)

    try:
        content = doPraseFileContent(GoogleDriveFileContent)
    except json.JSONDecodeError:
        return (jsonify({"error": str(e)}), 200)

    # 產生新的檔案名稱（帶時間戳記）
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_file_name = f"{GoogleDriveFileNam}_{now_str}.text"

    # 設定目標路徑
    dest_file_path = os.path.join(
        Google_AI_STUDIO_BACKUP_DIR, GoogleDriveFileNam, new_file_name
    )

    # 確保目錄存在
    dest_directory = os.path.dirname(dest_file_path)
    os.makedirs(dest_directory, exist_ok=True)

    # 寫入新檔案
    try:
        with open(dest_file_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        return (jsonify({"error": f"寫入檔案時發生錯誤: {str(e)}"}), 200)

    return (jsonify({"content": content}), 200)


def getGoogleDriveFileContent(GoogleDriveFileId):

    service = get_drive_service()
    if service is None:
        raise Exception("Drive service not available")

    # 這邊可以用來取得檔案名稱與mimeType，不過前面已經取得並過濾mimeType，先註解
    # try:
    #     meta = service.files().get(fileId=GoogleDriveFileId, fields="id,name,mimeType").execute()
    # except Exception as e:
    #     return (jsonify({"error": "Failed to fetch file metadata", "details": str(e)}), 500)
    # name = meta.get("name", "")
    # mime = meta.get("mimeType", "")

    FileContent = ""
    fh = io.BytesIO()
    try:
        request_media = service.files().get_media(fileId=GoogleDriveFileId)
        downloader = MediaIoBaseDownload(fh, request_media)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        FileContent = fh.getvalue().decode("utf-8", errors="replace")
    except Exception as e:
        raise Exception("Failed to download file content：" + str(e))

    return FileContent


def doPraseFileContent(FileContent):
    try:
        FileContent = json.loads(FileContent)
    except json.JSONDecodeError:
        raise Exception("非JSON格式")

    result = ""
    try:
        chunkedPrompt = FileContent.get("chunkedPrompt", None)
        if not chunkedPrompt == None:
            chunks = chunkedPrompt.get("chunks", None)

        if not chunks == None:
            for index, chunk in enumerate(chunks):
                role = chunk.get("role", "")
                isThought = chunk.get("isThought", "")
                text = chunk.get("text", "")
                if role == "model" and isThought == "":
                    result += text
                    result += (
                        "\n\n==================================================\n\n"
                    )

    except Exception as e:
        raise Exception("剖析JSON失敗，" + str(e))

    return result


@backup_Blueprint.route("/callback", methods=["GET"])
def callback():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=session["state"]
    )
    flow.redirect_uri = url_for("backup.callback", _external=True)
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    session["credentials"] = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }
    # return redirect(url_for("index"))
    return """
    <script>
        // 1. 通知母視窗（原本的網頁）重新整理，這樣母視窗就會觸發 index 路由去撈檔案
        if (window.opener) {
            window.opener.location.reload();
        }
        // 2. 關閉目前這個彈出的驗證小視窗
        window.close();
    </script>
    """
