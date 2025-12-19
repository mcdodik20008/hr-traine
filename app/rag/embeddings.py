"""
Embedding generator using sentence-transformers
"""
import logging
from typing import List
import numpy as np

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not installed")


class EmbeddingGenerator:
    """Generate embeddings using multilingual sentence transformer"""
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers is required. Install: pip install sentence-transformers")
        
        self.model_name = model_name
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"✅ Embedding model loaded, dimension: {self.dimension}")
    
    async def encode(self, text: str) -> np.ndarray:
        """Encode single text to embedding vector"""
        return self.model.encode(text, convert_to_numpy=True)
    
    async def encode_batch(self, texts: List[str]) -> np.ndarray:
        """Encode multiple texts to embedding vectors"""
        logger.info(f"Encoding {len(texts)} texts")
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
        logger.info(f"✅ Encoded {len(texts)} texts")
        return embeddings
