import os
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import EarlyStopping

from config import DATASET_PATH, MODEL_PATH, IMAGE_SIZE, BATCH_SIZE, EPOCHS, VALIDATION_SPLIT
from model import create_model


def main():
    datagen = ImageDataGenerator(
        rescale=1./255,
        validation_split=VALIDATION_SPLIT,
        rotation_range=30,
        zoom_range=0.2,
        width_shift_range=0.15,
        height_shift_range=0.15,
        shear_range=0.15,
        horizontal_flip=True,
        brightness_range=[0.7, 1.3]
    )

    train_data = datagen.flow_from_directory(
        DATASET_PATH,
        target_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        subset='training'
    )

    val_data = datagen.flow_from_directory(
        DATASET_PATH,
        target_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        subset='validation'
    )

    print("Urutan kelas (harus cocok sama CLASS_NAMES di config.py):", train_data.class_indices)

    #training model
    model = create_model()

    early_stop = EarlyStopping(monitor='val_accuracy', patience=3, restore_best_weights=True)

    model.fit(
        train_data,
        validation_data=val_data,
        epochs=EPOCHS,
        callbacks=[early_stop]
    )

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    model.save(MODEL_PATH)
    print(f"Model tersimpan di: {MODEL_PATH}")


if __name__ == "__main__":
    main()

print(train_data.class_indices)