import os
import re
import secrets
from datetime import datetime, timezone, timedelta

import boto3
from botocore.exceptions import ClientError
from flask import Flask, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", ""),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "1").lower() in ("1", "true", "yes"),
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    MAX_CONTENT_LENGTH=32 * 1024,
)

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
TABLE_NAME = os.environ.get("DDB_TABLE", "TF141")
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,24}$")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("FLASK_SECRET_KEY belum diatur. Atur environment variable sebelum menjalankan aplikasi.")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

ROLES = {
    "INFANTRY": {
        "name": "Infantry", "color": "#72d572",
        "description": "Tim lapangan yang menjaga komunikasi dan membantu warga di area terdampak."
    },
    "SPECIAL_FORCES": {
        "name": "Special Forces", "color": "#ff6868",
        "description": "Tim koordinasi khusus yang menangani informasi sensitif dan keputusan berisiko tinggi."
    },
    "AIRBORNE": {
        "name": "Airborne", "color": "#72d5ff",
        "description": "Tim penghubung udara yang membantu pemantauan dan koordinasi bantuan."
    },
    "AIR_FORCE": {
        "name": "Air Force Pilot", "color": "#568cff",
        "description": "Awak penerbangan yang menjaga keselamatan perjalanan dan jalur bantuan."
    },
    "STAFF": {
        "name": "Staff", "color": "#f0f3f7",
        "description": "Pusat koordinasi yang menyatukan laporan, logistik, dan komunikasi antartim."
    },
}

# Kelima perspektif mengikuti satu rangkaian peristiwa fiksi yang sama.
CAMPAIGN = [
    "Krisis komunikasi mulai muncul di kawasan Eropa Tengah.",
    "Gangguan layanan membuat beberapa komunitas kehilangan akses informasi.",
    "Laporan yang saling bertentangan mulai menyulitkan koordinasi bantuan.",
    "Koridor kemanusiaan membutuhkan pengaturan dan komunikasi yang lebih baik.",
    "Tim gabungan berusaha memulihkan layanan penting dan membangun kepercayaan.",
    "Seluruh unit menyatukan hasil kerja untuk menyelesaikan krisis dan mendukung pemulihan.",
]

MISSIONS = {
    "INFANTRY": [
        ("First Contact", "Berlin, Jerman", "Membantu warga dan membangun komunikasi awal di area terdampak."),
        ("Quiet District", "Prague, Ceko", "Memastikan kebutuhan komunitas tercatat dan diteruskan ke pusat koordinasi."),
        ("Broken Signal", "Gdansk, Polandia", "Mendukung pemulihan komunikasi bersama teknisi sipil."),
        ("Safe Passage", "Bratislava, Slovakia", "Membantu pengaturan informasi untuk jalur bantuan kemanusiaan."),
        ("Last Relay", "Vienna, Austria", "Menjaga pertukaran informasi antartim tetap jelas dan terverifikasi."),
        ("Homecoming", "Berlin, Jerman", "Mendukung proses pemulihan komunitas setelah krisis mereda."),
    ],
    "SPECIAL_FORCES": [
        ("Grey Ledger", "Prague, Ceko", "Memeriksa laporan penting dan menyusun gambaran situasi yang dapat dipercaya."),
        ("Silent Archive", "Warsaw, Polandia", "Melindungi catatan koordinasi dan memastikan informasi memiliki sumber."),
        ("False Horizon", "Budapest, Hungaria", "Membedakan kabar yang terverifikasi dari rumor yang beredar."),
        ("Cross Check", "Vienna, Austria", "Menyelaraskan laporan dari beberapa unit tanpa mengorbankan keselamatan warga."),
        ("Clear Signal", "Bratislava, Slovakia", "Membantu tim membangun saluran komunikasi yang dapat diandalkan."),
        ("Final Record", "Berlin, Jerman", "Menyusun catatan akhir untuk evaluasi dan pemulihan."),
    ],
    "AIRBORNE": [
        ("High Window", "Berlin, Jerman", "Menyampaikan gambaran umum kondisi wilayah kepada pusat koordinasi."),
        ("Blue Corridor", "Prague, Ceko", "Membantu koordinasi jalur bantuan dari sudut pandang udara."),
        ("Weather Hold", "Gdansk, Polandia", "Menilai perubahan kondisi dan menyampaikan pembaruan keselamatan."),
        ("Shared Horizon", "Bratislava, Slovakia", "Menyatukan laporan lapangan dan informasi penerbangan."),
        ("Open Channel", "Vienna, Austria", "Menjaga komunikasi antartim tetap konsisten selama operasi bantuan."),
        ("Return Window", "Berlin, Jerman", "Mendukung penutupan operasi dan pengembalian personel dengan aman."),
    ],
    "AIR_FORCE": [
        ("Departure Check", "Vienna, Austria", "Memastikan informasi penerbangan dan kebutuhan bantuan sudah terkoordinasi."),
        ("Clouded Route", "Prague, Ceko", "Menanggapi perubahan cuaca dan pembaruan keselamatan perjalanan."),
        ("Ground Link", "Gdansk, Polandia", "Menjaga komunikasi dengan petugas darat dan pusat bantuan."),
        ("Priority Cargo", "Bratislava, Slovakia", "Menyelaraskan prioritas pengiriman bantuan berdasarkan kebutuhan terverifikasi."),
        ("Night Beacon", "Warsaw, Polandia", "Mendukung koordinasi penerbangan dengan informasi yang jelas dan aman."),
        ("Safe Landing", "Berlin, Jerman", "Menuntaskan rangkaian penerbangan bantuan dan menyerahkan laporan akhir."),
    ],
    "STAFF": [
        ("Situation Room", "Berlin, Jerman", "Mengumpulkan laporan awal dan membentuk gambaran situasi bersama."),
        ("Supply Lines", "Warsaw, Polandia", "Mengatur kebutuhan logistik berdasarkan data yang sudah diperiksa."),
        ("Common Picture", "Prague, Ceko", "Menyatukan informasi dari semua unit dan mengurangi kesalahpahaman."),
        ("Civil Support", "Bratislava, Slovakia", "Menghubungkan kebutuhan warga dengan penyedia bantuan."),
        ("Recovery Plan", "Vienna, Austria", "Menyusun rencana pemulihan layanan bersama mitra sipil."),
        ("After Action", "Berlin, Jerman", "Menyusun evaluasi akhir dan rekomendasi untuk pemulihan."),
    ],
}

STEP_BEATS = [
    "Laporan pertama diterima dari petugas setempat.",
    "Pusat koordinasi meminta konfirmasi dari sumber kedua.",
    "Kebutuhan warga mulai dipetakan.",
    "Sebuah perubahan situasi membuat rencana awal perlu ditinjau.",
    "Dua laporan berbeda masuk hampir bersamaan.",
    "Tim teknis meminta prioritas yang jelas.",
    "Perwakilan komunitas menyampaikan kekhawatiran.",
    "Saluran komunikasi utama mengalami gangguan sementara.",
    "Unit lain mengirim pembaruan yang mengubah gambaran situasi.",
    "Tim harus menentukan prioritas berikutnya.",
    "Hasil koordinasi mulai terlihat, tetapi masih ada informasi yang perlu diperiksa.",
    "Pusat meminta keputusan akhir dan ringkasan hasil misi.",
]

CHOICES = [
    {"label": "Verifikasi informasi dengan sumber tepercaya", "detail": "Pastikan keputusan dibuat berdasarkan laporan yang dapat diperiksa.", "score": 2},
    {"label": "Koordinasikan keputusan dengan unit terkait", "detail": "Satukan informasi dan pastikan semua pihak memahami rencana.", "score": 1},
    {"label": "Bertindak berdasarkan laporan awal saja", "detail": "Keputusan cepat diambil sebelum seluruh informasi tersedia.", "score": -2},
]

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def user_pk(username):
    return f"USER#{username}"

def get_profile(username):
    result = table.get_item(Key={"PK": user_pk(username), "SK": "PROFILE"})
    return result.get("Item")

def get_role_progress(username, role):
    result = table.get_item(Key={"PK": user_pk(username), "SK": f"ROLE#{role}"})
    item = result.get("Item")
    if item:
        return item
    item = {
        "PK": user_pk(username),
        "SK": f"ROLE#{role}",
        "unlocked_mission": 1,
        "completed_missions": [],
        "active_mission": None,
        "step_index": 0,
        "score": 0,
        "choices": [],
        "status": "idle",
        "updated_at": now_iso(),
    }
    table.put_item(Item=item)
    return item

def save_role_progress(item):
    item["updated_at"] = now_iso()
    table.put_item(Item=item)

def api_error(message, status=400):
    return jsonify({"ok": False, "error": message}), status

def require_login():
    username = session.get("username")
    if not username:
        return None
    return username

@app.before_request
def csrf_protect():
    if request.path.startswith("/api/") and request.method in ("POST", "PUT", "PATCH", "DELETE"):
        token = session.get("csrf_token")
        supplied = request.headers.get("X-CSRF-Token", "")
        if not token or not secrets.compare_digest(token, supplied):
            return api_error("Sesi keamanan tidak valid. Muat ulang halaman lalu coba lagi.", 400)

@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "TASK FORCE 141 API"})

@app.get("/api/csrf")
def csrf():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return jsonify({"ok": True, "csrf_token": session["csrf_token"]})

@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if not USERNAME_RE.fullmatch(username):
        return api_error("Username harus 3–24 karakter dan hanya boleh berisi huruf, angka, atau underscore.")
    if len(password) < 8 or len(password) > 128:
        return api_error("Password harus terdiri dari 8–128 karakter.")

    normalized = username.lower()
    item = {
        "PK": user_pk(normalized),
        "SK": "PROFILE",
        "username": normalized,
        "password_hash": generate_password_hash(password),
        "active_role": None,
        "created_at": now_iso(),
    }
    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)"
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return api_error("Username tersebut sudah digunakan.", 409)
        app.logger.exception("DynamoDB register error")
        return api_error("Database belum dapat memproses pendaftaran.", 503)

    session.clear()
    session["username"] = normalized
    session["csrf_token"] = secrets.token_urlsafe(32)
    session.permanent = True
    return jsonify({"ok": True, "username": normalized, "csrf_token": session["csrf_token"]})

@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip().lower()
    password = str(data.get("password", ""))

    if not USERNAME_RE.fullmatch(username) or not password:
        return api_error("Username atau password tidak sesuai.", 401)
    try:
        profile = get_profile(username)
    except ClientError:
        app.logger.exception("DynamoDB login error")
        return api_error("Database belum dapat diakses.", 503)

    if not profile or not check_password_hash(profile.get("password_hash", ""), password):
        return api_error("Username atau password tidak sesuai.", 401)

    session.clear()
    session["username"] = username
    session["csrf_token"] = secrets.token_urlsafe(32)
    session.permanent = True
    return jsonify({"ok": True, "username": username, "csrf_token": session["csrf_token"]})

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})

@app.get("/api/me")
def me():
    username = require_login()
    if not username:
        return jsonify({"ok": True, "authenticated": False})
    try:
        profile = get_profile(username)
    except ClientError:
        app.logger.exception("DynamoDB profile error")
        return api_error("Database belum dapat diakses.", 503)
    return jsonify({
        "ok": True,
        "authenticated": bool(profile),
        "username": username,
        "active_role": profile.get("active_role") if profile else None,
    })

@app.get("/api/game/state")
def game_state():
    username = require_login()
    if not username:
        return api_error("Silakan login terlebih dahulu.", 401)
    try:
        profile = get_profile(username)
        if not profile:
            session.clear()
            return api_error("Akun tidak ditemukan. Silakan login kembali.", 401)
        progress = {}
        for role in ROLES:
            item = get_role_progress(username, role)
            progress[role] = {
                "unlocked_mission": int(item.get("unlocked_mission", 1)),
                "completed_missions": item.get("completed_missions", []),
                "active_mission": item.get("active_mission"),
                "step_index": int(item.get("step_index", 0)),
                "score": int(item.get("score", 0)),
                "status": item.get("status", "idle"),
            }
        return jsonify({
            "ok": True, "username": username,
            "active_role": profile.get("active_role"),
            "roles": ROLES, "missions": {
                role: [{"number": i + 1, "title": m[0], "location": m[1], "brief": m[2]}
                       for i, m in enumerate(MISSIONS[role])]
                for role in MISSIONS
            },
            "progress": progress,
        })
    except ClientError:
        app.logger.exception("DynamoDB game state error")
        return api_error("Tidak dapat membaca progres permainan dari DynamoDB.", 503)

@app.post("/api/role")
def select_role():
    username = require_login()
    if not username:
        return api_error("Silakan login terlebih dahulu.", 401)
    data = request.get_json(silent=True) or {}
    role = data.get("role")
    if role not in ROLES:
        return api_error("Role tidak dikenal.")
    try:
        table.update_item(
            Key={"PK": user_pk(username), "SK": "PROFILE"},
            UpdateExpression="SET active_role = :role",
            ExpressionAttributeValues={":role": role},
        )
        get_role_progress(username, role)
        return jsonify({"ok": True, "active_role": role})
    except ClientError:
        app.logger.exception("DynamoDB role selection error")
        return api_error("Tidak dapat menyimpan pilihan role.", 503)

@app.post("/api/mission/start")
def start_mission():
    username = require_login()
    if not username:
        return api_error("Silakan login terlebih dahulu.", 401)
    data = request.get_json(silent=True) or {}
    role, number = data.get("role"), data.get("mission")
    if role not in ROLES or not isinstance(number, int) or not 1 <= number <= 6:
        return api_error("Role atau nomor misi tidak valid.")
    try:
        progress = get_role_progress(username, role)
        completed = progress.get("completed_missions", [])
        if number > int(progress.get("unlocked_mission", 1)) and number not in completed:
            return api_error("Misi ini masih terkunci.", 403)
        progress.update({
            "active_mission": number,
            "step_index": 0,
            "score": 0,
            "choices": [],
            "status": "active",
            "result": None,
        })
        save_role_progress(progress)
        table.update_item(
            Key={"PK": user_pk(username), "SK": "PROFILE"},
            UpdateExpression="SET active_role = :role",
            ExpressionAttributeValues={":role": role},
        )
        return jsonify({"ok": True, "role": role, "mission": number})
    except ClientError:
        app.logger.exception("DynamoDB start mission error")
        return api_error("Tidak dapat memulai misi.", 503)

@app.get("/api/mission/current")
def current_mission():
    username = require_login()
    if not username:
        return api_error("Silakan login terlebih dahulu.", 401)
    role = request.args.get("role")
    if role not in ROLES:
        return api_error("Pilih role terlebih dahulu.")
    try:
        progress = get_role_progress(username, role)
        number = progress.get("active_mission")
        if not number:
            return api_error("Belum ada misi aktif.", 404)
        mission = MISSIONS[role][int(number) - 1]
        idx = int(progress.get("step_index", 0))
        finished = progress.get("status") in ("success", "failed")
        history = progress.get("choices", [])
        carryover = ""
        if history and not finished:
            previous_choice = history[-1].get("choice")
            if previous_choice == 0:
                carryover = "Dampak keputusan sebelumnya: laporan yang sudah diverifikasi membuat pusat koordinasi memiliki dasar informasi yang lebih kuat. "
            elif previous_choice == 1:
                carryover = "Dampak keputusan sebelumnya: koordinasi antartim berjalan lebih teratur, meskipun beberapa detail masih perlu dikonfirmasi. "
            else:
                carryover = "Dampak keputusan sebelumnya: keputusan yang terlalu cepat menimbulkan pertanyaan lanjutan, sehingga tim perlu memperjelas informasi. "
        return jsonify({
            "ok": True,
            "role": role,
            "role_name": ROLES[role]["name"],
            "mission": int(number),
            "mission_title": mission[0],
            "location": mission[1],
            "brief": mission[2],
            "step_index": idx,
            "total_steps": 12,
            "score": int(progress.get("score", 0)),
            "status": progress.get("status", "idle"),
            "result": progress.get("result"),
            "choices": progress.get("choices", []),
            "step": None if finished else {
                "number": idx + 1,
                "beat": STEP_BEATS[idx],
                "campaign_context": CAMPAIGN[int(number) - 1],
                "narrative": (
                    f"{mission[2]} {carryover}{STEP_BEATS[idx]} "
                    f"Sebagai {ROLES[role]['name']}, kamu menerima pembaruan dari pusat koordinasi. "
                    "Pilih respons yang paling bertanggung jawab untuk menjaga informasi dan keselamatan semua pihak."
                ),
                "options": [{"label": c["label"], "detail": c["detail"]} for c in CHOICES],
            }
        })
    except ClientError:
        app.logger.exception("DynamoDB current mission error")
        return api_error("Tidak dapat membaca misi aktif.", 503)

@app.post("/api/mission/choose")
def choose_step():
    username = require_login()
    if not username:
        return api_error("Silakan login terlebih dahulu.", 401)
    data = request.get_json(silent=True) or {}
    role, choice_index = data.get("role"), data.get("choice")
    if role not in ROLES or not isinstance(choice_index, int) or choice_index not in (0, 1, 2):
        return api_error("Pilihan tidak valid.")
    try:
        progress = get_role_progress(username, role)
        if progress.get("status") != "active" or not progress.get("active_mission"):
            return api_error("Tidak ada misi aktif.")
        idx = int(progress.get("step_index", 0))
        if idx >= 12:
            return api_error("Misi sudah mencapai tahap akhir.")
        choice = CHOICES[choice_index]
        history = progress.get("choices", [])
        history.append({"step": idx + 1, "choice": choice_index, "label": choice["label"]})
        score = int(progress.get("score", 0)) + choice["score"]
        if idx < 11:
            progress["step_index"] = idx + 1
            progress["score"] = score
            progress["choices"] = history
            save_role_progress(progress)
            return jsonify({"ok": True, "finished": False, "step_index": idx + 1})
        success = score >= 0
        mission_no = int(progress["active_mission"])
        completed = progress.get("completed_missions", [])
        if success and mission_no not in completed:
            completed.append(mission_no)
        progress.update({
            "step_index": 12,
            "score": score,
            "choices": history,
            "status": "success" if success else "failed",
            "result": "success" if success else "failed",
            "completed_missions": completed,
            "unlocked_mission": min(6, max(int(progress.get("unlocked_mission", 1)), mission_no + 1)) if success else int(progress.get("unlocked_mission", 1)),
        })
        save_role_progress(progress)
        return jsonify({
            "ok": True, "finished": True, "result": progress["result"],
            "completed_missions": completed,
            "unlocked_mission": progress["unlocked_mission"],
            "campaign_complete": success and len(completed) == 6,
        })
    except ClientError:
        app.logger.exception("DynamoDB choose step error")
        return api_error("Tidak dapat menyimpan pilihan misi.", 503)

@app.errorhandler(413)
def too_large(_error):
    return api_error("Permintaan terlalu besar.", 413)

@app.errorhandler(500)
def server_error(_error):
    app.logger.exception("Unhandled server error")
    return api_error("Terjadi kesalahan pada server.", 500)

if __name__ == "__main__":
    # Untuk pengembangan lokal saja. Produksi gunakan Gunicorn di belakang Apache.
    app.run(host="127.0.0.1", port=5000, debug=False)
