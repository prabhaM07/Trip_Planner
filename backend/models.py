import os
from langchain_groq import ChatGroq
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer
from typing import List
import itertools
from dotenv import load_dotenv 
load_dotenv()

API_KEYS = os.getenv("GROQ_API_KEYS", "").split(",")
if not API_KEYS or API_KEYS == [""]:
    raise RuntimeError("No GROQ_API_KEYS found")

# Infinite round-robin key rotation
key_cycle = itertools.cycle(API_KEYS)


def get_llm_model(api_key : str):
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.2,     
        max_tokens=1000,
        api_key = api_key,   
    )

def get_llm():
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.2,     
        max_tokens=1000,
        api_key = API_KEYS[0],
    )

def invoke_llm(messages):
    last_error = None

    for _ in range(len(API_KEYS)):
        api_key = next(key_cycle)
        try:
            return get_llm_model(api_key).invoke(messages)
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"All Groq API keys failed: {last_error}")


class SentenceTransformerEmbeddings(Embeddings):
    
    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5"):
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        
        # Embed a list of documents.
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def embed_query(self, text: str) -> List[float]:
        
        # Embed a single query.
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()



def get_embedding_model():
    return SentenceTransformerEmbeddings(
        model_name="BAAI/bge-base-en-v1.5"
    )