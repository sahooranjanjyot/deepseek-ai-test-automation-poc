from typing import List
from rag_retrieve import get_context


def format_rules_block(rules: List[str], version: str = "gherkin_contract.v1") -> str:
    """
    Deterministic rule injection block.
    This is how RAG rules are 'tagged' so the LLM always sees them.
    """
    cleaned = [r.strip() for r in rules if r and r.strip()]
    numbered = "\n".join(f"{i+1}. {r}" for i, r in enumerate(cleaned))

    return (
        f"[RAG_RULES::{version}]\n"
        f"{numbered}\n"
        f"[/RAG_RULES]\n"
    )


def build_prompt(user_story_or_task: str) -> str:
    """
    Builds the final prompt by injecting RAG context and governance rules.
    """
    rag = get_context(user_story_or_task)

    # If your get_context() already returns "rules", keep it.
    # If it returns only text, we wrap it into rules as a single entry.
    rules = rag.get("rules") if isinstance(rag, dict) else None
    context_text = rag.get("context") if isinstance(rag, dict) else str(rag)

    if not rules:
        rules = [context_text]

    rules_block = format_rules_block(rules)

    prompt = f"""
You are a senior test automation engineer.

{rules_block}

SYSTEM CONTEXT:
{context_text}

TASK:
{user_story_or_task}

Return output that strictly follows the rules above.
""".strip()

    return prompt


if __name__ == "__main__":
    print(build_prompt("Generate Salesforce Vehicle Ordering scenario"))