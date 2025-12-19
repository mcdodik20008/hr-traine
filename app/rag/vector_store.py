"""
FAISS vector store for fast similarity search
"""
import logging
from pathlib import Path
from typing import List, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("faiss not installed")

try:
    import pickle
except ImportError:
    pickle = None


class FAISSVectorStore:
    """In-memory vector store using FAISS for similarity search"""
    
    def __init__(self, dimension: int = 384):
        if not FAISS_AVAILABLE:
            raise ImportError("faiss-cpu is required. Install: pip install faiss-cpu")
        
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)  # L2 distance
        self.documents = []
        logger.info(f"✅ FAISS index created with dimension {dimension}")
    
    def add_documents(self, embeddings: np.ndarray, documents: List[Dict[str, Any]]):
        """
        Add documents with their embeddings to the index
        
        Args:
            embeddings: numpy array of shape (n_docs, dimension)
            documents: list of document metadata dicts
        """
        if len(embeddings) != len(documents):
            raise ValueError("Number of embeddings must match number of documents")
        
        # Add to FAISS index
        self.index.add(embeddings.astype('float32'))
        
        # Store document metadata
        self.documents.extend(documents)
        
        logger.info(f"✅ Added {len(documents)} documents to index. Total: {len(self.documents)}")
    
    def search(self, query_embedding: np.ndarray, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Search for similar documents
        
        Args:
            query_embedding: query vector
            top_k: number of results to return
            
        Returns:
            List of documents with similarity scores
        """
        if len(self.documents) == 0:
            logger.warning("Vector store is empty")
            return []
        
        # Ensure query is 2D
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Search
        distances, indices = self.index.search(
            query_embedding.astype('float32'), 
            min(top_k, len(self.documents))
        )
        
        # Build results
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.documents) and idx != -1:
                doc = self.documents[idx].copy()
                doc['score'] = float(distance)  # Lower is better for L2
                results.append(doc)
        
        logger.debug(f"Found {len(results)} results for query")
        return results
    
    def save(self, filepath: Path):
        """Save index and documents to disk"""
        if not pickle:
            raise ImportError("pickle is required for saving")
        
        filepath = Path(filepath)
        filepath.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        index_file = filepath / "index.faiss"
        faiss.write_index(self.index, str(index_file))
        
        # Save documents metadata
        docs_file = filepath / "documents.pkl"
        with open(docs_file, "wb") as f:
            pickle.dump(self.documents, f)
        
        logger.info(f"✅ Saved index to {filepath}")
    
    def load(self, filepath: Path):
        """Load index and documents from disk"""
        if not pickle:
            raise ImportError("pickle is required for loading")
        
        filepath = Path(filepath)
        
        # Load FAISS index
        index_file = filepath / "index.faiss"
        if not index_file.exists():
            raise FileNotFoundError(f"Index file not found: {index_file}")
        
        self.index = faiss.read_index(str(index_file))
        
        # Load documents metadata
        docs_file = filepath / "documents.pkl"
        if not docs_file.exists():
            raise FileNotFoundError(f"Documents file not found: {docs_file}")
        
        with open(docs_file, "rb") as f:
            self.documents = pickle.load(f)
        
        logger.info(f"✅ Loaded {len(self.documents)} documents from {filepath}")
    
    @property
    def size(self) -> int:
        """Return number of documents in the store"""
        return len(self.documents)
