import pickle
import numpy as np

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct
)

print("Connecting to Qdrant...")

client = QdrantClient(path="./qdrant_db")

# Create collection if not exists
try:
    client.create_collection(
        collection_name="sql_lectures",
        vectors_config=VectorParams(
            size=1024,
            distance=Distance.COSINE
        )
    )
    print("Collection created.")
except:
    print("Collection already exists.")

# Load embeddings
embeddings = np.load("embeddings.npy")

# Load chunks
with open("chunks.pkl", "rb") as f:
    chunks = pickle.load(f)

print(f"Loaded {len(chunks)} chunks")

points = []

for idx, (embedding, chunk) in enumerate(
    zip(embeddings, chunks)
):

    points.append(
        PointStruct(
            id=idx,
            vector=embedding.tolist(),
            payload={
                "text": chunk["text"],
                "source": chunk["source"]
            }
        )
    )

client.upsert(
    collection_name="sql_lectures",
    points=points
)

print(f"Inserted {len(points)} chunks into Qdrant")