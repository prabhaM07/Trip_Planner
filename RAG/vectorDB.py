from pathlib import Path
from typing import List
from langchain_chroma import Chroma
from langchain_core.documents import Document


class VectorStoreManager:
    def __init__(self, persist_dir: Path, embedding_model):
        self.persist_dir = persist_dir
        self.embedding_model = embedding_model
        self.vector_store: Chroma | None = None

    def initialize_vector_store(self) -> Chroma:
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.vector_store = Chroma(
            collection_name="rag_collection",
            embedding_function=self.embedding_model,
            persist_directory=str(self.persist_dir),
        )

        return self.vector_store

    def store_documents(self, chunks: List[Document], batch_size: int = 10) -> int:
        if self.vector_store is None:
            raise ValueError("Vector store not initialized")

        valid_chunks = [c for c in chunks if c.page_content.strip()]
        if not valid_chunks:
            raise ValueError("All chunks are empty")

        total = len(valid_chunks)

        for i in range(0, total, batch_size):
            batch = valid_chunks[i : i + batch_size]
            self.vector_store.add_documents(batch)
            print(f"Stored {min(i + batch_size, total)}/{total} chunks")

        return total

    def get_document_count(self) -> int:
        if self.vector_store is None:
            return 0
        return self.vector_store._collection.count()

    def clear_vector_store(self):
        
        if self.vector_store is None:
            return

        data = self.vector_store.get(include=["ids"])
        ids = data.get("ids", [])

        if not ids:
            print("Vector store already empty")
            return

        self.vector_store._collection.delete(ids=ids)
        print(f"Deleted {len(ids)} documents from vector store")
