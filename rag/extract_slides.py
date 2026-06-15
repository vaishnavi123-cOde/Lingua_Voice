import cv2
import os

VIDEO_FOLDER = "."
FRAME_FOLDER = "slides"

os.makedirs(FRAME_FOLDER, exist_ok=True)

for video in os.listdir(VIDEO_FOLDER):

    if not video.endswith(".mp4"):
        continue

    path = os.path.join(VIDEO_FOLDER, video)

    cap = cv2.VideoCapture(path)

    fps = cap.get(cv2.CAP_PROP_FPS)

    frame_interval = int(fps * 30)

    count = 0
    saved = 0

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        if count % frame_interval == 0:

            filename = (
                f"{video}_{saved}.jpg"
            )

            cv2.imwrite(
                os.path.join(
                    FRAME_FOLDER,
                    filename
                ),
                frame
            )

            saved += 1

        count += 1

    cap.release()

    print(video, "->", saved, "frames")