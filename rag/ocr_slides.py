import os
import easyocr

reader = easyocr.Reader(['en'])

SLIDE_DIR = "unique_slides"
OUTPUT_DIR = "slide_texts"

os.makedirs(OUTPUT_DIR, exist_ok=True)

count = 0

for image in os.listdir(SLIDE_DIR):

    path = os.path.join(
        SLIDE_DIR,
        image
    )

    try:

        result = reader.readtext(
            path,
            detail=0
        )

        text = "\n".join(result)

        with open(
            os.path.join(
                OUTPUT_DIR,
                image + ".txt"
            ),
            "w",
            encoding="utf-8"
        ) as f:

            f.write(text)

        count += 1

        if count % 25 == 0:
            print("Processed:", count)

    except Exception as e:
        print(image, e)

print("Finished:", count)