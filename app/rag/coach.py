"""
Real-Time HR Coach using RAG
"""
import logging
from typing import Dict, List, Optional, Any
from app.rag.vector_store import FAISSVectorStore
from app.rag.embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


class HRCoach:
    """Real-time coaching for interviewers using RAG"""
    
    def __init__(self, vector_store: FAISSVectorStore, embedding_gen: EmbeddingGenerator):
        self.vector_store = vector_store
        self.embedding_gen = embedding_gen
        logger.info("✅ HR Coach initialized")
    
    async def analyze_question(
        self, 
        question: str, 
        context: Optional[List[Dict]] = None,
        top_k: int = 3,
        score_threshold: float = 1.2
    ) -> Dict[str, Any]:
        """
        Analyze interviewer's question and provide feedback
        
        Args:
            question: The question asked by the interviewer
            context: Optional conversation history
            top_k: Number of similar documents to retrieve
            score_threshold: Maximum L2 distance for relevance (lower is more similar)
            
        Returns:
            {
                "has_feedback": bool,
                "severity": "info" | "tip" | "warning",
                "message": str,
                "category": str,
                "matched_patterns": list  # For prohibited questions
            }
        """
        try:
            # Generate embedding for the question
            question_embedding = await self.embedding_gen.encode(question.lower())
            
            # Search for similar documents
            results = self.vector_store.search(question_embedding, top_k=top_k)
            
            if not results:
                logger.debug("No results found")
                return {"has_feedback": False}
            
            # Check for prohibited questions by patterns first
            prohibited_match = self._check_prohibited_patterns(question, results)
            if prohibited_match:
                return prohibited_match
            
            # Filter by score threshold (L2 distance)
            relevant = [r for r in results if r['score'] < score_threshold]
            
            if not relevant:
                logger.debug(f"No relevant results (all scores > {score_threshold})")
                return {"has_feedback": False}
            
            # Select best feedback
            feedback = self._select_best_feedback(relevant)
            
            return {
                "has_feedback": True,
                "severity": feedback['severity'],
                "message": self._format_message(feedback),
                "category": feedback['category'],
                "score": feedback['score']
            }
            
        except Exception as e:
            logger.error(f"Error analyzing question: {e}", exc_info=True)
            return {"has_feedback": False}
    
    def _check_prohibited_patterns(
        self, 
        question: str, 
        results: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """Check if question contains prohibited patterns"""
        question_lower = question.lower()
        
        for result in results:
            if result.get('category') == 'prohibited':
                patterns = result.get('patterns', [])
                
                # Check if any pattern matches
                for pattern in patterns:
                    if pattern.lower() in question_lower:
                        logger.info(f"Prohibited pattern matched: '{pattern}'")
                        return {
                            "has_feedback": True,
                            "severity": "warning",
                            "message": self._format_message(result),
                            "category": "prohibited",
                            "matched_patterns": [pattern]
                        }
        
        return None
    
    def _select_best_feedback(self, results: List[Dict]) -> Dict:
        """
        Select the most important feedback from results
        Priority: warning > tip > info
        """
        priority = {"warning": 3, "tip": 2, "info": 1}
        
        # Sort by severity (descending) then by score (ascending - lower is better)
        sorted_results = sorted(
            results,
            key=lambda x: (priority.get(x.get('severity', 'info'), 0), -x['score']),
            reverse=True
        )
        
        return sorted_results[0]
    
    def _format_message(self, feedback: Dict) -> str:
        """Format feedback message with emoji"""
        emoji_map = {
            "warning": "⚠️",
            "tip": "💡",
            "info": "ℹ️"
        }
        
        severity = feedback.get('severity', 'info')
        content = feedback.get('content', '')
        emoji = emoji_map.get(severity, "ℹ️")
        
        return f"{emoji} {content}"


# Global instances (will be initialized by init script)
_hr_coach: Optional[HRCoach] = None


def get_hr_coach() -> Optional[HRCoach]:
    """Get global HR Coach instance"""
    return _hr_coach


def set_hr_coach(coach: HRCoach):
    """Set global HR Coach instance"""
    global _hr_coach
    _hr_coach = coach
    logger.info("✅ Global HR Coach instance set")
