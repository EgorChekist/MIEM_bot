from typing import List
from sklearn.metrics.pairwise import cosine_similarity


class SemanticChunker:
    """
    Semantic chunking по смыслу.
    По абзацам.
    """

    def __init__(
        self,
        embedding_model,
        max_chunk_size: int = 900,
        similarity_threshold: float = 0.6,
        batch_size: int = 8,
    ):
        self.embedding_model = embedding_model
        self.max_chunk_size = max_chunk_size
        self.similarity_threshold = similarity_threshold
        self.batch_size = batch_size

    def embed_in_batches(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = self.embedding_model.embed_documents(batch)
            embeddings.extend(batch_embeddings)
        return embeddings

    def chunk_text(self, text: str) -> List[str]:
        paragraphs = [
            p.strip()
            for p in text.split("\n\n")
            if p.strip()
        ]

        if len(paragraphs) <= 1:
            return paragraphs

        embeddings = self.embed_in_batches(paragraphs)

        chunks = []
        current_chunk = [paragraphs[0]]
        current_len = len(paragraphs[0])

        for i in range(1, len(paragraphs)):
            similarity = cosine_similarity(
                [embeddings[i - 1]],
                [embeddings[i]],
            )[0][0]

            next_len = current_len + len(paragraphs[i])

            if (
                similarity >= self.similarity_threshold
                and next_len <= self.max_chunk_size
            ):
                current_chunk.append(paragraphs[i])
                current_len = next_len
            else:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [paragraphs[i]]
                current_len = len(paragraphs[i])

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks