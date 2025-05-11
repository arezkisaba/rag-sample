import os
import sys
from typing import Dict, Any, Optional, List
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import numpy as np

LLM_MODEL_NAME = "gemma3:12b"
# LLM_MODEL_NAME = "llama3.1:8b"
EMBEDDING_MODEL_NAME = "nomic-embed-text"

class SimpleEmbeddings(Embeddings):
    """A simple embedding class that uses a basic approach to generate embeddings."""
    
    def __init__(self, dimensionality: int = 384):
        """Initialize with specified dimensionality."""
        self.dimensionality = dimensionality
    
    def _get_simple_embedding(self, text: str) -> List[float]:
        """Create a simple deterministic embedding based on the text content."""
        # Use a hash of the text to seed the random generator for consistency
        text_hash = hash(text) % (2**32)
        np.random.seed(text_hash)
        
        # Generate a random vector
        vector = np.random.normal(0, 1, self.dimensionality)
        
        # Normalize to unit length
        vector = vector / np.linalg.norm(vector)
        
        return vector.tolist()
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        return [self._get_simple_embedding(text) for text in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a query."""
        return self._get_simple_embedding(text)

def load_readme(readme_path: str) -> Optional[str]:
    try:
        print(readme_path)
        with open(readme_path, "r") as file:
            content = file.read()
        return content
    except FileNotFoundError:
        print(f"sample file not found at {readme_path}")
        return None

def create_vector_store(text_content: str) -> FAISS:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    
    docs = [Document(page_content=text_content)]
    chunks = text_splitter.split_documents(docs)
    
    try:
        print(f"Trying to use Ollama embeddings with {EMBEDDING_MODEL_NAME}...")
        try:
            from langchain_ollama import OllamaEmbeddings
        except ImportError:
            from langchain_community.embeddings import OllamaEmbeddings
            
        embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL_NAME)
        _ = embeddings.embed_query("test")
        print("Successfully using Ollama for embeddings")
    except Exception as e:
        print(f"Could not use Ollama embeddings: {e}")
        print("Falling back to simple local embeddings")
        embeddings = SimpleEmbeddings()
    
    vector_store = FAISS.from_documents(chunks, embeddings)
    
    return vector_store

def create_rag_chain(vector_store: FAISS) -> Dict[str, Any]:
    """
    Create a RAG chain using the vector store
    """
    # Create retriever
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3}
    )
    
    # Create LLM using local Ollama with Gemma model
    # Import from newer package if available
    try:
        from langchain_ollama import OllamaLLM
        llm = OllamaLLM(model=LLM_MODEL_NAME)
    except ImportError:
        from langchain_community.llms import Ollama
        llm = Ollama(model=LLM_MODEL_NAME)
    
    # Create prompt template
    template = """
    You are an assistant that answers questions based on the provided context.
    
    Context:
    {context}
    
    Question: {question}
    
    Answer the question based only on the provided context. If you cannot answer the question from the context, say "I don't have enough information to answer this question."
    """
    
    prompt = ChatPromptTemplate.from_template(template)
    
    # Create RAG chain
    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain

def main() -> None:
    baseFolder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    readme_content = load_readme(f'{os.path.join(baseFolder, "resources", "sample.md")}')

    print(readme_content)

    print(f"Creating vector store with embeddings using {EMBEDDING_MODEL_NAME}...")
    vector_store = create_vector_store(readme_content)
    
    print(f"Creating RAG chain with Ollama LLM using {LLM_MODEL_NAME}...")
    rag_chain = create_rag_chain(vector_store)
    
    print("RAG system initialized with sample content")
    response = rag_chain.invoke("What is Bioprinted Infrastructure relative to ?")
    print("\nResponse:")
    print(response)

if __name__ == "__main__":
    main()