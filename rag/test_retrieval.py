from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "BAAI/bge-large-en-v1.5"
)

client = QdrantClient(
    path="./qdrant_db"
)

while True:

    question = input(
        "\nAsk: "
    )

    query = model.encode(
        question,
        normalize_embeddings=True
    ).tolist()

    results = client.query_points(
        collection_name="sql_lectures",
        query=query,
        limit=20
    ).points

    print("\nTOP RESULTS:\n")

    for i, r in enumerate(results):

        print(
            f"\n{i+1}. Score:",
            round(r.score,4)
        )

        print(
            "Source:",
            r.payload["source"]
        )

        print(
            r.payload["text"][:300]
        )