"""
Initialize RAG knowledge base and create FAISS index
"""
import asyncio
import json
import logging
from pathlib import Path
from app.rag.vector_store import FAISSVectorStore
from app.rag.embeddings import EmbeddingGenerator
from app.rag.coach import HRCoach, set_hr_coach

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def initialize_rag():
    """Initialize RAG system: load knowledge base and create vector index"""
    
    logger.info("🚀 Initializing RAG system...")
    
    # Paths
    project_root = Path(__file__).parent.parent.parent
    knowledge_dir = project_root / "app" / "data" / "knowledge"
    index_path = project_root / "app" / "data" / "rag_index"
    
    # Check if index already exists
    if (index_path / "index.faiss").exists():
        logger.info("📦 Loading existing RAG index...")
        embedding_gen = EmbeddingGenerator()
        vector_store = FAISSVectorStore(dimension=embedding_gen.dimension)
        vector_store.load(index_path)
        
        coach = HRCoach(vector_store, embedding_gen)
        set_hr_coach(coach)
        
        logger.info(f"✅ RAG system loaded with {vector_store.size} documents")
        return coach
    
    # Load all knowledge base files
    logger.info("📚 Loading knowledge base files...")
    all_docs = []
    
    json_files = list(knowledge_dir.glob("*.json"))
    
    if not json_files:
        raise FileNotFoundError(f"No knowledge base files found in {knowledge_dir}")
    
    for json_file in json_files:
        logger.info(f"  Loading {json_file.name}...")
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            docs = data.get('documents', [])
            all_docs.extend(docs)
            logger.info(f"    ✅ Loaded {len(docs)} documents")
    
    logger.info(f"📊 Total documents loaded: {len(all_docs)}")
    
    # Generate embeddings
    logger.info("🔢 Generating embeddings...")
    embedding_gen = EmbeddingGenerator()
    
    texts = [doc['content'] for doc in all_docs]
    embeddings = await embedding_gen.encode_batch(texts)
    
    logger.info(f"✅ Generated {len(embeddings)} embeddings")
    
    # Create vector store
    logger.info("💾 Creating FAISS index...")
    vector_store = FAISSVectorStore(dimension=embedding_gen.dimension)
    vector_store.add_documents(embeddings, all_docs)
    
    # Save index
    logger.info(f"💾 Saving index to {index_path}...")
    vector_store.save(index_path)
    
    # Create and set global coach
    coach = HRCoach(vector_store, embedding_gen)
    set_hr_coach(coach)
    
    logger.info("=" * 60)
    logger.info(f"✅ RAG system initialized successfully!")
    logger.info(f"📊 Documents: {vector_store.size}")
    logger.info(f"📁 Index saved to: {index_path}")
    logger.info("=" * 60)
    
    return coach


async def test_coach():
    """Test the coach with sample questions"""
    coach = await initialize_rag()
    
    test_questions = [
        "Сколько вам лет?",
        "Расскажите о вашем опыте работы",
        "Вы умеете работать в команде?",
        "Какие у вас планы на детей?",
        "Опишите проект, которым вы гордитесь"
    ]
    
    print("\n" + "=" * 60)
    print("🧪 Testing HR Coach")
    print("=" * 60)
    
    for question in test_questions:
        print(f"\n❓ Вопрос: {question}")
        feedback = await coach.analyze_question(question)
        
        if feedback['has_feedback']:
            print(f"   {feedback['message']}")
            print(f"   [Category: {feedback['category']}, Severity: {feedback['severity']}]")
        else:
            print("   ✅ No feedback (question looks good)")


if __name__ == "__main__":
    # Initialize RAG
    asyncio.run(initialize_rag())
    
    # Uncomment to test
    # asyncio.run(test_coach())
