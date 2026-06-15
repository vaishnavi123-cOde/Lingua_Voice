import os
import shutil

TRANSCRIPT_DIR = "transcripts"
OCR_DIR = "slide_texts"
OUTPUT_DIR = "combined_docs"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Copy transcripts
for file in os.listdir(TRANSCRIPT_DIR):

    if file.endswith(".txt"):

        src = os.path.join(
            TRANSCRIPT_DIR,
            file
        )

        dst = os.path.join(
            OUTPUT_DIR,
            f"transcript_{file}"
        )

        shutil.copy(src, dst)

# Copy OCR files
for file in os.listdir(OCR_DIR):

    if file.endswith(".txt"):

        src = os.path.join(
            OCR_DIR,
            file
        )

        dst = os.path.join(
            OUTPUT_DIR,
            f"ocr_{file}"
        )

        shutil.copy(src, dst)

print(
    "Total files:",
    len(os.listdir(OUTPUT_DIR))
)