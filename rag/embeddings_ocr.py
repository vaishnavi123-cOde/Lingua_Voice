import pickle
import numpy as np

from sentence_transformers import SentenceTransformer

print("Loading BGE model...")

model = SentenceTransformer(
    "BAAI/bge-large-en-v1.5"
)

with open(
    "chunks.pkl",
    "rb"
) as f:

    chunks = pickle.load(f)

texts = [
    chunk["text"]
    for chunk in chunks
]

print(
    "Chunks:",
    len(texts)
)

embeddings = model.encode(
    texts,
    batch_size=16,
    show_progress_bar=True,
    normalize_embeddings=True
)

np.save(
    "embeddings_ocr.npy",
    embeddings
)

print(
    "Embeddings shape:",
    embeddings.shape
)