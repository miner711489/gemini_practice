import json
from flask import (
    Flask,
    render_template,
)
import os
from history import history_Blueprint
from detail import detail_Blueprint
from backup import backup_Blueprint

# 加入這行來允許 HTTP 連線 (僅限開發環境使用)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# --- 全域設定 ---
app = Flask(__name__)

"""錯誤原因：
在 Flask 中，session 是用來儲存使用者狀態（例如 OAuth 的 state 或登入資訊）的。
為了防止資料被竄改，Flask 要求你必須設定一個 secret_key（密鑰）來加密這些資料。
因為你目前的程式碼中沒有設定這個密鑰，所以當執行到 session['state'] = state 時，程式就崩潰了。
"""
app.secret_key = "your_secret_key"  # 隨便填

app.register_blueprint(history_Blueprint, url_prefix="/history")
app.register_blueprint(detail_Blueprint, url_prefix="/detail")
app.register_blueprint(backup_Blueprint, url_prefix="/backup")


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
