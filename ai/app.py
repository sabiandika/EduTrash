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


load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN") 
POINTS_PER_DETECTION = 10

POINTS_COOLDOWN_SECONDS = 60

#level setiap poinnya
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

if ALLOWED_ORIGIN:
    CORS(app, origins=[ALLOWED_ORIGIN])
else:
    CORS(app)

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