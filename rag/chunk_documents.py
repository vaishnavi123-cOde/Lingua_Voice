import os
import pickle

DOCS_DIR = "combined_docs"

chunks = []

CHUNK_SIZE = 500
OVERLAP = 100

for file in os.listdir(DOCS_DIR):

    if not file.endswith(".txt"):
        continue

    path = os.path.join(
        DOCS_DIR,
        file
    )

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as f:

            text = f.read()

        text = text.strip()

        if len(text) < 20:
            continue

        start = 0

        while start < len(text):

            chunk_text = text[
                start:
                start + CHUNK_SIZE
            ]

            chunks.append(
                {
                    "text": chunk_text,
                    "source": file
                }
            )

            start += (
                CHUNK_SIZE - OVERLAP
            )

    except Exception as e:

        print(
            "Error:",
            file,
            e
        )

with open(
    "chunks.pkl",
    "wb"
) as f:

    pickle.dump(
        chunks,
        f
    )

print(
    "Total Chunks:",
    len(chunks)
)