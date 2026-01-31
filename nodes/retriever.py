from pathlib import Path
from travelstate import TravelState
from RAG.retriever import Retriever
from models import get_embedding_model
from langfuse import observe


# Purpose:
# This node retrieves the most relevant text chunks from a PDF-based vector store based on the user's query. 
# It is responsible for loading the PDF, extracting text, chunking content, creating embeddings, and performing retrieval.
# 
# PDF Loading:
# - Uses Path from pathlib to handle PDF file paths
# 
# Text Extraction:
# The PDF content is extracted using two methods:
#   1. PdfReader (PyPDF) – Extracts embedded digital text from PDFs
#   2. OCR (pytesseract) – Optical Character Recognition used as a fallback
#      when the PDF contains scanned images instead of text
# 
# Chunking:
# - Extracted text is split into manageable chunks using RecursiveCharacterTextSplitter
# 
# Embedding Model:
# - Uses SentenceTransformerEmbeddings
# - Model: "BAAI/bge-base-en-v1.5"
# 
#  Vector Store:
#  - Uses ChromaDB to store and manage document embeddings
# 
#  Retrieval Techniques:
# - Lexical Search: BM25 retriever (keyword-based matching)
# - Vector Search: Similarity-based retrieval using embeddings
#
# Output:
# - Returns the retrieved document chunks


@observe(name="retriever_node")
def retriever_node(state: TravelState,llm):
    
    user_query = state.get("user_query", "")
    pdf_path = Path(state.get("pdf_path", ""))
    vector_created = state.get("vector_created", False)
    flag = False
    
    if not vector_created:
        
        flag = True
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
    retriever = Retriever(
        pdf_path=pdf_path,
        embedding_model=get_embedding_model()
    )

    retriever.initialize(rebuild=flag)

    docs = retriever.retrieve(user_query)
   
    return {
        "retrieved_docs": docs,
        "vector_created": True
    }
