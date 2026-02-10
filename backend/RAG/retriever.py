from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever

from RAG.loadPDF import PDFProcessor
from RAG.chunking import DocumentChunker
from RAG.vectorDB import VectorStoreManager

class Retriever:
    def __init__(
        self,
        pdf_path: str,
        embedding_model,
        persist_dir: str = "chroma_db",
        max_tokens: int = 3500,
        chunk_overlap: int = 200,
        k: int = 10,  
        top_n: int = 5,  
    ):
        self.pdf_path = Path(pdf_path)
        self.persist_dir = Path(persist_dir)
        self.max_tokens = max_tokens
        self.chunk_overlap = chunk_overlap
        self.k = k
        self.top_n = top_n
        self.embedding_model = embedding_model
        self.vector_store = None
        self.retriever = None
        self.chunks = []

    def initialize(self, rebuild: bool = False):
        
        # Load PDF
        pdf_processor = PDFProcessor(self.pdf_path)
        docs = pdf_processor.load()

        # Chunk
        chunker = DocumentChunker(
            max_tokens=self.max_tokens,
            chunk_overlap=self.chunk_overlap,
        )
        self.chunks = chunker.chunk(docs)

        # Vector store
        vector_manager = VectorStoreManager(
            persist_dir=self.persist_dir,
            embedding_model=self.embedding_model,
        )

        if rebuild:
            vector_manager.clear_vector_store()

        self.vector_store = vector_manager.initialize_vector_store()

        if vector_manager.get_document_count() == 0:
            vector_manager.store_documents(self.chunks)

    
        self._setup_retriever()

    # hybrid retriever
    def _setup_retriever(self):
        
        # BM25 retriever for lexical search
        bm25 = BM25Retriever.from_documents(self.chunks, k=self.k)
        
        # Vector retriever with similarity search
        vector = self.vector_store.as_retriever(
            search_type="similarity", 
            search_kwargs={
                "k": self.k,
            },
        )

        # Ensemble retriever (hybrid)
        self.retriever = EnsembleRetriever(
            retrievers=[vector, bm25],
            weights=[0.6, 0.4], 
        )

    def retrieve(self, query: str) -> List[Document]:
        if self.retriever is None:
            raise RuntimeError("Retriever not initialized")
        
        results = self.retriever.invoke(query)

        return results[:self.top_n]
    
    def retrieve_vector_only(self, query: str) -> List[Document]:
        
        if self.vector_store is None:
            raise RuntimeError("Vector store not initialized")
        
        return self.vector_store.as_retriever(
            search_kwargs={"k": self.top_n}
        ).invoke(query)