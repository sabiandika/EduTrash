import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# dataset 
DATASET_PATH = os.path.join(PROJECT_ROOT, "dataset")
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "model_sampah.h5")

# ngasih label
LABELS_PATH = os.path.join(BASE_DIR, "labels.json")

IMAGE_SIZE = (150, 150)

#training
BATCH_SIZE = 16
EPOCHS = 20
VALIDATION_SPLIT = 0.2
LEARNING_RATE = 0.001

#prediksi
CONF_THRESHOLD = 0.75

#
CLASS_NAMES = ["Anorganik", "Organik"]