"""
Single, stable entrypoint for all RAG context used by LLM generators.

Do NOT import rag_retrieve.get_context directly from generator scripts.
Always call get_llm_context() so we can enforce contracts centrally later.
"""

from rag_retrieve import get_context


def get_llm_context(question: str, k: int = 3) -> str:
    """
    Returns retrieval-augmented context for a given question.

    Args:
        question: Natural language question / instruction.
        k: Number of top matches to retrieve from the vector index.
    """
    return get_context(question, k=k)
