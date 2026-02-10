from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentChunker:
    def __init__(self, max_tokens: int = 3500, chunk_overlap: int = 200):
        self.chunk_size = max_tokens * 4
        self.chunk_overlap = chunk_overlap * 4

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

    def chunk(self, docs: List[Document]) -> List[Document]:
        chunks = self.text_splitter.split_documents(docs)

        if not chunks:
            raise ValueError("No chunks created")

        return chunks
