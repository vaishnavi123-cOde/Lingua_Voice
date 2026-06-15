import os
import cv2
import imagehash

from PIL import Image

SLIDES_DIR = "slides"
UNIQUE_DIR = "unique_slides"

os.makedirs(UNIQUE_DIR, exist_ok=True)

seen = set()
saved = 0

for file in os.listdir(SLIDES_DIR):

    path = os.path.join(SLIDES_DIR, file)

    try:
        img = Image.open(path)

        h = imagehash.phash(img)

        if h not in seen:
            seen.add(h)

            img.save(
                os.path.join(
                    UNIQUE_DIR,
                    file
                )
            )

            saved += 1

    except:
        pass

print("Unique slides:", saved)