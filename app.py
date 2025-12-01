import json
from flask import (
    Flask,
    render_template,
)
from history import history_Blueprint
from detail import detail_Blueprint

# --- 全域設定 ---
app = Flask(__name__)
app.register_blueprint(history_Blueprint, url_prefix="/history")
app.register_blueprint(detail_Blueprint, url_prefix="/detail")


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
