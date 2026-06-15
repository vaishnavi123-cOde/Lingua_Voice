import os
import pickle

TRANSCRIPT_DIR = "transcripts"

chunks = []

CHUNK_SIZE = 250

for file in os.listdir(TRANSCRIPT_DIR):

    if not file.endswith(".txt"):
        continue

    path = os.path.join(TRANSCRIPT_DIR, file)

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    words = text.split()

    for i in range(0, len(words), CHUNK_SIZE):

        chunk = " ".join(words[i:i + CHUNK_SIZE])

        chunks.append({
            "source": file,
            "text": chunk
        })

print("Total chunks:", len(chunks))

with open("chunks.pkl", "wb") as f:
    pickle.dump(chunks, f)

print("Saved chunks.pkl")