from flask import Blueprint, request, render_template, render_template_string
import requests
import os
import json
from datetime import datetime
from flask import jsonify
from config import RUN_DIR_PATH_three
import base64

# 創建一個 Blueprint 物件
detail_Blueprint = Blueprint("detail", __name__)

# 先沒用到的py，先丟上來
@detail_Blueprint.route("/apd", methods=["POST"])
def getBase64():
    id = request.get_json().get("id")
    filename = request.get_json().get("filename")
    return ""


