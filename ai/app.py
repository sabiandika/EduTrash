from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import tensorflow as tf
import json

from config import MODEL_PATH, LABELS_PATH, CONF_THRESHOLD, CLASS_NAMES
from utils import preprocess_frame, read_image_file

app = Flask(__name__)
CORS(app)  # biar bisa diakses dari domain/port lain (frontend beda port)

# ================= LOAD MODEL & LABELS SEKALI DI AWAL (bukan tiap request) =================
print("Loading model...")
try:
    model = tf.keras.models.load_model(MODEL_PATH)
except Exception:
    print(f"Gagal load model dari {MODEL_PATH}")
    print("Pastiin file model_sampah.h5 udah ada di folder models/, atau jalanin train.py dulu.")
    raise




with open(LABELS_PATH, encoding="utf-8") as f:
    text = f.read()

print(text)

labels_info = json.loads(text)


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

        return jsonify({
            "success": True,
            "detected": True,
            "prediction": class_name,
            "confidence": round(confidence * 100, 1),
            "description": info.get("description", ""),
            "bin": info.get("bin", ""),
            "management": info.get("management", ""),
            "disposal_tip": info.get("disposal_tip", "")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "AI service jalan", "endpoint": "/predict (POST, form-data key: image)"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)