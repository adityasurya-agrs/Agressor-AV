
import os
import re
import logging
from datetime import datetime, timezone
from functools import wraps

import boto3
from flask import Flask, request, jsonify, session, send_from_directory
from botocore.exceptions import ClientError
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=None)

SECRET = os.environ.get("FLASK_SECRET_KEY")
if not SECRET:
    raise RuntimeError("FLASK_SECRET_KEY belum diatur!")

app.secret_key = SECRET
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "true").lower() == "true",
    PERMANENT_SESSION_LIFETIME=28800
)

logging.basicConfig(level=logging.INFO)

REGION = os.getenv("AWS_REGION", "us-east-1")
TABLE_NAME = os.getenv("DDB_TABLE", "TF141")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

ROLES = {
    "infantry",
    "special",
    "airborne",
    "airforce",
    "staff"
}


def response_error(message, status=400):
    return jsonify({
        "ok": False,
        "error": message
    }), status


def authenticated(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("username"):
            return response_error("Silakan login terlebih dahulu.", 401)
        return func(*args, **kwargs)
    return wrapper


def player_key():
    return "USER#" + session["username"].lower()


def get_player():
    result = table.get_item(
        Key={
            "pk": player_key(),
            "sk": "PROFILE"
        }
    )
    return result.get("Item")


@app.get("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "application": "TASK FORCE 141"
    })


@app.post("/api/register")
def register():

    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,20}", username):
        return response_error(
            "Username harus 3-20 karakter dan hanya boleh memakai huruf, angka, titik, garis bawah, atau tanda hubung."
        )

    if not 8 <= len(password) <= 128:
        return response_error("Password harus 8-128 karakter.")

    item = {
        "pk": "USER#" + username.lower(),
        "sk": "PROFILE",
        "username": username,
        "password_hash": generate_password_hash(password),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "role": None,
        "completed": {}
    }

    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(pk)"
        )

    except ClientError as e:

        if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return response_error("Username sudah digunakan.", 409)

        app.logger.exception("Register error")
        return response_error("Gagal menyimpan akun ke DynamoDB.", 500)

    session.clear()
    session["username"] = username
    session.permanent = True

    return jsonify({
        "ok": True,
        "username": username,
        "role": None,
        "completed": {}
    })


@app.post("/api/login")
def login():

    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if not username or not password:
        return response_error("Username dan password harus diisi.")

    try:
        result = table.get_item(
            Key={
                "pk": "USER#" + username.lower(),
                "sk": "PROFILE"
            }
        )

        item = result.get("Item")

    except ClientError:
        app.logger.exception("Login error")
        return response_error("DynamoDB tidak dapat dihubungi.", 500)

    if not item or not check_password_hash(
        item.get("password_hash", ""),
        password
    ):
        return response_error("Username atau password salah.", 401)

    session.clear()
    session["username"] = item["username"]
    session.permanent = True

    return jsonify({
        "ok": True,
        "username": item["username"],
        "role": item.get("role"),
        "completed": item.get("completed", {})
    })


@app.post("/api/logout")
@authenticated
def logout():

    session.clear()

    return jsonify({"ok": True})


@app.get("/api/me")
@authenticated
def me():

    try:
        item = get_player()

        if not item:
            session.clear()
            return response_error("Akun tidak ditemukan.", 404)

        return jsonify({
            "ok": True,
            "username": item["username"],
            "role": item.get("role"),
            "completed": item.get("completed", {})
        })

    except ClientError:
        app.logger.exception("Profile error")
        return response_error("Gagal membaca profil.", 500)


@app.post("/api/role")
@authenticated
def save_role():

    data = request.get_json(silent=True) or {}
    role = data.get("role")

    if role not in ROLES:
        return response_error("Role tidak valid.")

    try:
        table.update_item(
            Key={
                "pk": player_key(),
                "sk": "PROFILE"
            },
            UpdateExpression="SET #r = :r",
            ExpressionAttributeNames={
                "#r": "role"
            },
            ExpressionAttributeValues={
                ":r": role
            }
        )

        return jsonify({
            "ok": True,
            "role": role
        })

    except ClientError:
        app.logger.exception("Role update error")
        return response_error("Gagal menyimpan role.", 500)


@app.post("/api/progress")
@authenticated
def save_progress():

    data = request.get_json(silent=True) or {}

    role = data.get("role")
    mission = data.get("mission")
    ending = data.get("ending")

    if role not in ROLES:
        return response_error("Role tidak valid.")

    if type(mission) is not int or not 1 <= mission <= 6:
        return response_error("Nomor misi tidak valid.")

    if ending not in ("good", "bad"):
        return response_error("Ending tidak valid.")

    try:
        item = get_player()

        if not item:
            return response_error("Akun tidak ditemukan.", 404)

        completed = item.get("completed", {})

        previous = completed.get(
            f"{role}#{mission-1}", {}
        )

        if mission > 1 and not previous.get("success", False):
            return response_error(
                "Selesaikan misi sebelumnya terlebih dahulu.",
                403
            )

        key = f"{role}#{mission}"

        old_success = completed.get(key, {}).get(
            "success", False
        )

        success = old_success or ending == "good"

        completed[key] = {
            "success": success,
            "ending": ending,
            "played_at": datetime.now(timezone.utc).isoformat()
        }

        table.update_item(
            Key={
                "pk": player_key(),
                "sk": "PROFILE"
            },
            UpdateExpression="SET completed = :c",
            ExpressionAttributeValues={
                ":c": completed
            }
        )

        return jsonify({
            "ok": True,
            "completed": completed
        })

    except ClientError:
        app.logger.exception("Progress update error")
        return response_error("Gagal menyimpan progres.", 500)


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
