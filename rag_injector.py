from rag_retrieve import get_context

def build_prompt(user_story_or_task: str):
    context = get_context(user_story_or_task)

    prompt = f"""
You are a senior test automation engineer.

RULES:
- Use ONLY the SYSTEM CONTEXT provided.
- Do NOT invent UI elements, navigation, or business rules.
- If something is missing, state it explicitly as TODO.

SYSTEM CONTEXT:
{context}

TASK:
{user_story_or_task}
"""
    return prompt
