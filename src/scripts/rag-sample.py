import os
import sys
import glob
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

def load_markdown_files(resource_dir: str) -> List[Document]:
    """Load all markdown files from the resources directory."""
    markdown_files = glob.glob(os.path.join(resource_dir, "*.md"))
    documents = []
    
    for file_path in markdown_files:
        try:
            with open(file_path, "r") as file:
                content = file.read()
                file_name = os.path.basename(file_path)
                doc = Document(page_content=content, metadata={"source": file_name})
                documents.append(doc)
                print(f"Loaded {file_name}")
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    
    return documents

def create_vector_store(documents: List[Document]) -> FAISS:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    
    chunks = text_splitter.split_documents(documents)
    print(f"Split documents into {len(chunks)} chunks")
    
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
        search_kwargs={"k": 5}  # Increased from 3 to 5 to get more context from diverse documents
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
    You are an assistant that answers questions based on the provided context from multiple documents.
    
    Context:
    {context}
    
    Question: {question}
    
    Answer the question based only on the provided context. If you cannot answer the question from the context, say "I don't have enough information to answer this question."
    
    If relevant, mention which document(s) in the context contain information used for your answer.
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
    base_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    resources_dir = os.path.join(base_folder, "resources")
    
    print(f"Loading documents from {resources_dir}...")
    documents = load_markdown_files(resources_dir)
    
    if not documents:
        print("No documents found. Exiting.")
        return
    
    print(f"Creating vector store with embeddings using {EMBEDDING_MODEL_NAME}...")
    vector_store = create_vector_store(documents)
    
    print(f"Creating RAG chain with Ollama LLM using {LLM_MODEL_NAME}...")
    rag_chain = create_rag_chain(vector_store)
    
    print(f"RAG system initialized with {len(documents)} documents")
    
    # Updated to a more comprehensive query that could span multiple documents
    response = rag_chain.invoke("Describe the different applications of bioprinting technology across various fields")
    
    print("\nResponse:")
    print(response)

if __name__ == "__main__":
    main()