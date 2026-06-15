import pickle
import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "BAAI/bge-large-en-v1.5"
)

with open("chunks.pkl", "rb") as f:
    chunks = pickle.load(f)

texts = [chunk["text"] for chunk in chunks]

embeddings = model.encode(
    texts,
    show_progress_bar=True
)

np.save("embeddings.npy", embeddings)

print("Embeddings shape:", embeddings.shape)