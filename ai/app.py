import os
import json
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import numpy as np
import tensorflow as tf

from config import MODEL_PATH, LABELS_PATH, CONF_THRESHOLD, CLASS_NAMES
from utils import preprocess_frame, read_image_file

# ================= ENV VARS =================
# Lokal: dibaca dari file .env (lihat .env.example)
# Production (Render dll): dibaca dari Environment Variables di dashboard hosting,
# load_dotenv() otomatis gak ngapa-ngapain kalau file .env-nya emang gak ada.
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN")  # contoh: https://edutrash.vercel.app
POINTS_PER_DETECTION = 10

# Kamera scan sekarang jalan terus-menerus (gak berhenti otomatis pas
# ketemu 1 deteksi), jadi kita batesin poin CUMA bisa didapet sekali
# tiap COOLDOWN_SECONDS, biar orang gak bisa curang cuma diemin kamera
# ke 1 barang buat farming poin. Ini dicek dari SERVER (tabel `detections`),
# bukan dari frontend, jadi gak bisa diakalin.
POINTS_COOLDOWN_SECONDS = 60

# ================= LEVEL / BADGE =================
# CATATAN PENTING: kalau daftar ini diubah, samain juga LEVELS di web/levels.js
# biar badge yang ditampilin di frontend konsisten sama yang dihitung di sini.
LEVELS = [
    {"name": "Pemula Peduli", "emoji": "🌱", "min_points": 0},
    {"name": "Pemilah Sampah", "emoji": "🗑️", "min_points": 20},
    {"name": "Ksatria Daur Ulang", "emoji": "♻️", "min_points": 50},
    {"name": "Pahlawan Sampah", "emoji": "🦸", "min_points": 100},
    {"name": "Pejuang Lingkungan", "emoji": "🌍", "min_points": 200},
    {"name": "Master Pemilah", "emoji": "🏅", "min_points": 350},
    {"name": "Duta Lingkungan", "emoji": "🌿", "min_points": 550},
    {"name": "Legenda Daur Ulang", "emoji": "👑", "min_points": 800},
    {"name": "Penyelamat Bumi", "emoji": "🌏", "min_points": 1200},
    {"name": "EduTrash Grandmaster", "emoji": "🏆", "min_points": 1700},
]


def get_level(points):
    current = LEVELS[0]
    for lvl in LEVELS:
        if points >= lvl["min_points"]:
            current = lvl
    return current

app = Flask(__name__)

# Kalau ALLOWED_ORIGIN diisi (production), CORS dibatesin cuma buat domain itu doang.
# Kalau kosong (dev lokal), izinin semua origin biar gampang testing.
if ALLOWED_ORIGIN:
    CORS(app, origins=[ALLOWED_ORIGIN])
else:
    CORS(app)

# ================= SUPABASE ADMIN CLIENT (OPSIONAL) =================
# Dipake buat verifikasi token user & nambah poin dari SISI SERVER.
# Pake service_role key -> PUNYA AKSES PENUH, makanya cuma boleh ada di sini
# (backend), gak pernah dikirim ke frontend/browser.
# Kalau env var belum diisi, fitur poin otomatis nonaktif tapi fitur
# scan/predict inti tetap jalan normal (aman buat siapa aja coba tanpa akun).
supabase_admin = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    try:
        from supabase import create_client
        supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("Supabase admin client siap, fitur poin aktif.")
    except Exception as e:
        print(f"Gagal inisialisasi Supabase admin client, fitur poin nonaktif: {e}")
else:
    print("SUPABASE_URL/SUPABASE_SERVICE_KEY belum diisi, fitur poin nonaktif (scan tetap jalan).")


def get_authenticated_user_id():
    """
    Ambil token dari header 'Authorization: Bearer <token>' yang dikirim
    frontend, terus VERIFIKASI ke server Supabase langsung (bukan percaya
    mentah-mentah isi token dari client). Kalau gak ada token / token gak
    valid / expired -> return None (dianggap gak login, request tetep
    diproses tapi tanpa poin).
    """
    if not supabase_admin:
        return None

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None

    try:
        user_response = supabase_admin.auth.get_user(token)
        return user_response.user.id
    except Exception:
        return None


def award_points_and_log(user_id, class_name, confidence_pct):
    """
    Nambah poin + catet riwayat deteksi - TAPI cuma kalau user gak lagi
    kena cooldown (belum dapet poin dalam POINTS_COOLDOWN_SECONDS terakhir).
    Fungsi ini CUMA dipanggil dari server pake service_role key, jadi
    user gak bisa manggil ini langsung dari browser buat curang.
    """
    try:
        # ================= CEK COOLDOWN =================
        last_detection = (
            supabase_admin.table("detections")
            .select("created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if last_detection.data:
            last_time_str = last_detection.data[0]["created_at"].replace("Z", "+00:00")
            last_time = datetime.fromisoformat(last_time_str)
            elapsed = (datetime.now(timezone.utc) - last_time).total_seconds()
            if elapsed < POINTS_COOLDOWN_SECONDS:
                return {
                    "awarded": False,
                    "on_cooldown": True,
                    "cooldown_remaining": round(POINTS_COOLDOWN_SECONDS - elapsed)
                }

        # ================= NAMBAH POIN =================
        profile = (
            supabase_admin.table("profiles")
            .select("points")
            .eq("id", user_id)
            .single()
            .execute()
        )
        current_points = profile.data["points"] if profile.data else 0
        new_points = current_points + POINTS_PER_DETECTION

        supabase_admin.table("profiles").update({"points": new_points}).eq("id", user_id).execute()
        supabase_admin.table("detections").insert({
            "user_id": user_id,
            "prediction": class_name,
            "confidence": confidence_pct
        }).execute()

        level_before = get_level(current_points)
        level_after = get_level(new_points)

        return {
            "awarded": True,
            "on_cooldown": False,
            "total_points": new_points,
            "level_name": level_after["name"],
            "level_emoji": level_after["emoji"],
            "leveled_up": level_before["name"] != level_after["name"]
        }
    except Exception as e:
        print(f"Gagal nyimpen poin/riwayat buat user {user_id}: {e}")
        return None


# ================= LOAD MODEL & LABELS SEKALI DI AWAL (bukan tiap request) =================
print("Loading model...")
try:
    model = tf.keras.models.load_model(MODEL_PATH)
except Exception:
    print(f"Gagal load model dari {MODEL_PATH}")
    print("Pastiin file model_sampah.h5 udah ada di folder models/, atau jalanin train.py dulu.")
    raise

with open(LABELS_PATH, encoding="utf-8") as f:
    labels_info = json.load(f)

print("Model siap.")


@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return jsonify({"error": "Gak ada file 'image' di request"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "File kosong"}), 400

    try:
        frame_bgr = read_image_file(file)
        if frame_bgr is None:
            return jsonify({"error": "Gagal baca gambar, pastiin format-nya valid (jpg/png)"}), 400

        img = preprocess_frame(frame_bgr)
        pred = model.predict(img, verbose=0)
        confidence = float(np.max(pred))
        class_name = CLASS_NAMES[int(np.argmax(pred))]

        if confidence < CONF_THRESHOLD:
            return jsonify({
                "success": True,
                "detected": False,
                "message": "Objek gak dikenali dengan yakin, coba foto ulang dengan latar netral & cahaya terang."
            })

        info = labels_info.get(class_name, {})
        confidence_pct = round(confidence * 100, 1)

        # ================= NAMBAH POIN (SERVER-SIDE, GAK BISA DICURANGI) =================
        user_id = get_authenticated_user_id()
        points_awarded = False
        total_points = None
        level_name = None
        level_emoji = None
        leveled_up = False
        on_cooldown = False
        cooldown_remaining = None

        if user_id:
            result = award_points_and_log(user_id, class_name, confidence_pct)
            if result is not None:
                if result["awarded"]:
                    points_awarded = True
                    total_points = result["total_points"]
                    level_name = result["level_name"]
                    level_emoji = result["level_emoji"]
                    leveled_up = result["leveled_up"]
                elif result["on_cooldown"]:
                    on_cooldown = True
                    cooldown_remaining = result["cooldown_remaining"]

        return jsonify({
            "success": True,
            "detected": True,
            "prediction": class_name,
            "confidence": confidence_pct,
            "description": info.get("description", ""),
            "bin": info.get("bin", ""),
            "management": info.get("management", ""),
            "disposal_tip": info.get("disposal_tip", ""),
            "how_to": info.get("how_to", ""),
            "points_awarded": points_awarded,
            "total_points": total_points,
            "level_name": level_name,
            "level_emoji": level_emoji,
            "leveled_up": leveled_up,
            "on_cooldown": on_cooldown,
            "cooldown_remaining": cooldown_remaining
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "AI service jalan", "endpoint": "/predict (POST, form-data key: image)"})


if __name__ == "__main__":
    app.run(debug=True, port=5000) 
    app.run(host="0.0.0.0", port=port, debug=False)