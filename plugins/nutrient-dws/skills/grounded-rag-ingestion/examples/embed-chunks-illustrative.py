# ILLUSTRATIVE ONLY — not a supported script.
#
# This file shows how chunks emitted by chunk.py flow into an embedder while keeping their
# provenance (chunk_id + bbox + page_index) attached to each embedding record. Swap `openai`
# for your provider. It intentionally has NO `uv` script block and is not runnable without
# manually installing a provider SDK. No embedding library is a dependency of this skill —
# the skill's boundary is the chunk JSONL.
#
# Security: read the provider key from the environment; never hardcode it.

import json
import os
import sys

# import openai  # provider of your choice — install manually


def main(jsonl_path: str) -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("Set OPENAI_API_KEY in the environment; do not hardcode keys.")
    # client = openai.OpenAI(api_key=api_key)

    with open(jsonl_path, encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f if line.strip()]

    texts = [c["text"] for c in chunks]
    # resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
    # embeddings = [d.embedding for d in resp.data]
    embeddings = [[0.0] for _ in texts]  # placeholder; replace with the call above

    for chunk, vector in zip(chunks, embeddings):
        # The provenance fields survive into the embedding record — this is the whole point.
        record = {
            "id": chunk["chunk_id"],
            "embedding": vector,
            "metadata": {
                "page_index": chunk["page_index"],
                "bbox": chunk["bbox"],
                "source_doc": chunk["source_doc"],
                "element_type": chunk["element_type"],
            },
            "text": chunk["text"],
        }
        print(json.dumps(record))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python embed-chunks-illustrative.py chunks.jsonl")
    main(sys.argv[1])
