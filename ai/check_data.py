import os
from PIL import Image

from config import DATASET_PATH

bad_files = []
checked = 0

print(f"Ngecek gambar di: {DATASET_PATH}\n")

for root, dirs, files in os.walk(DATASET_PATH):
    for fname in files:
        fpath = os.path.join(root, fname)
        checked += 1
        try:
            with Image.open(fpath) as img:
                img.verify()  # cek struktur file-nya gambarnya valid apa enggak
        except Exception:
            bad_files.append(fpath)
            print(f"RUSAK: {fpath}")

print(f"\nTotal dicek : {checked} file")
print(f"Rusak       : {len(bad_files)} file")

if bad_files:
    jawaban = input("\nHapus semua file yang rusak di atas? (y/n): ")
    if jawaban.strip().lower() == "y":
        for f in bad_files:
            os.remove(f)
        print(f"{len(bad_files)} file rusak udah dihapus.")
    else:
        print("Gak dihapus. Daftar file rusak ada di atas kalau mau dicek/hapus manual.")
else:
    print("Semua file aman, gak ada yang rusak.")