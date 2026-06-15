import pickle
import numpy as np

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct
)

print("Loading data...")

with open(
    "chunks.pkl",
    "rb"
) as f:
    chunks = pickle.load(f)

embeddings = np.load(
    "embeddings_ocr.npy"
)

print(
    "Chunks:",
    len(chunks)
)

print(
    "Embeddings:",
    embeddings.shape
)

client = QdrantClient(
    path="./qdrant_db"
)

COLLECTION = "sql_lectures"

try:
    client.delete_collection(
        COLLECTION
    )

    print(
        "Old collection removed."
    )

except:
    pass

client.create_collection(
    collection_name=COLLECTION,

    vectors_config=VectorParams(
        size=1024,
        distance=Distance.COSINE
    )
)

print(
    "Collection created."
)

points = []

for idx, chunk in enumerate(chunks):

    points.append(
        PointStruct(
            id=idx,

            vector=embeddings[idx].tolist(),

            payload={
                "text":
                chunk["text"],

                "source":
                chunk["source"]
            }
        )
    )

client.upsert(
    collection_name=COLLECTION,
    points=points
)

print(
    "Inserted",
    len(points),
    "points into Qdrant"
)