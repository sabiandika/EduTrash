import cv2
import numpy as np

from config import IMAGE_SIZE


def preprocess_frame(frame_bgr):
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, IMAGE_SIZE)
    normalized = resized / 255.0
    return np.reshape(normalized, (1, *IMAGE_SIZE, 3))


def read_image_file(file_storage):
    file_bytes = np.frombuffer(file_storage.read(), np.uint8)
    frame_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    return frame_bgr