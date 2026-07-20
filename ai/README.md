# EduTrash - Klasifikasi Sampah Organik/Anorganik

EduTrash adalah aplikasi sederhana buat ngenalin jenis sampah (organik/anorganik) dari foto, pake model machine learning (TensorFlow/Keras). Backend-nya jalan pake Flask, dan tampilan buat testing/demo-nya ada di file `demo.html`.

## Struktur Folder

```
EduTrash/
└── ai/
    ├── app.py              # Flask backend (server API)
    ├── config.py           # Konfigurasi model, label, threshold
    ├── utils.py             # Fungsi bantu (baca & preprocess gambar)
    ├── train.py             # Script buat training model
    ├── check_data.py        # Script buat cek dataset
    ├── model.py              # Definisi arsitektur model
    ├── labels.json           # Info detail tiap kelas sampah
    ├── demo.html              # Halaman demo/testing (frontend sederhana)
    ├── models/                # Folder tempat model hasil training disimpan
    └── dataset/
        ├── organik/
        └── anorganik/
```

## Yang Perlu Disiapin

- Python 3.9 - 3.11 (disaranin, biar kompatibel sama TensorFlow)
- Model sudah ditraining (file `.h5` ada di folder `models/`). Kalau belum ada, jalanin `train.py` dulu.

## Cara Install

1. Buat virtual environment (opsional tapi disaranin):

   ```bash
   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # Mac/Linux
   ```

2. Install semua library yang dibutuhin:
   ```bash
   pip install -r requirements.txt
   ```

## Cara Menjalankan

1. Masuk ke folder `ai/`:

   ```bash
   cd EduTrash/ai
   ```

2. Jalanin server backend-nya:

   ```bash
   python app.py
   ```

3. Tunggu sampai muncul tulisan `Model siap.` di terminal. Ini artinya server udah nyala dan siap nerima request di:

   ```
   http://127.0.0.1:5000
   ```

   > **Catatan:** Kalau kamu buka alamat itu langsung di browser, yang muncul itu bukan tampilan/UI, tapi respons JSON status server, contohnya:
   >
   > ```json
   > {
   >   "status": "AI service jalan",
   >   "endpoint": "/predict (POST, form-data key: image)"
   > }
   > ```
   >
   > Itu **normal**, karena `127.0.0.1:5000` itu alamat backend/API-nya doang, bukan halaman web.

4. Buat nyoba aplikasinya (upload foto & liat hasil deteksi), buka file **`demo.html`**:
   - Cara paling gampang: klik kanan file `demo.html` di file explorer/code editor → pilih **Open with Live Server** (kalau pake VS Code + extension Live Server), atau
   - Bisa juga langsung double click file `demo.html`, nanti otomatis kebuka di browser default.

5. Pastiin backend (`python app.py`) tetap jalan di terminal selagi kamu pake `demo.html`, soalnya `demo.html` bakal ngirim request foto ke `http://127.0.0.1:5000/predict` di belakang layar.

## Alur Pemakaian Singkat

1. Jalanin `python app.py` → biarin terminal tetap nyala.
2. Buka `demo.html` di browser.
3. Upload/pilih foto sampah.
4. Hasil klasifikasi (organik/anorganik, tingkat keyakinan, tips pembuangan, dll) bakal muncul di halaman tersebut.

## Troubleshooting

- **Buka `127.0.0.1:5000` malah muncul `demo.html`, bukan JSON status** → biasanya ini bukan dari `app.py`, tapi karena tab preview (Simple Browser VS Code) atau Live Server nyangkut di cache/port yang sama. Coba tutup semua tab preview, matiin proses Live Server, lalu buka `127.0.0.1:5000` di browser biasa (Chrome/Edge).
- **Muncul error "Gagal load model"** → pastiin file model (`.h5`) sudah ada di folder `models/`. Kalau belum, jalanin `python train.py` dulu buat training modelnya.
- **`demo.html` gak bisa connect ke backend** → cek lagi apakah `python app.py` masih jalan di terminal, dan pastiin alamat API di dalam `demo.html` sudah sesuai (`http://127.0.0.1:5000/predict`).
