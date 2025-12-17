import sys
import json

from rag.retrieve import retrieve
from tools.llm.local_client import chat_completion


def generate_testcase(task: str) -> dict:
    # --- RAG ---
    rag_results = retrieve(task, top_k=5)

    rag_context = "\n".join([r.get("content", "") for r in rag_results]).strip()
    if not rag_context:
        raise SystemExit("RAG_EMPTY")

    # --- PROMPT ---
    prompt = f"""
You are a QA test case generator.

Return ONLY valid JSON. No markdown. No explanation.

JSON FORMAT:
{{
  "header": {{
    "test_case_id": "TC-001",
    "jira_ref": "JIRA-001",
    "test_case_description": "{task}",
    "pre_requisites": [],
    "test_data": [],
    "priority": "High"
  }},
  "steps": [
    {{
      "action": "Navigate to Home Page",
      "expected_result": "Home Page is displayed"
    }}
  ]
}}

RULES:
- Each step MUST contain exactly ONE action
- Use ONLY navigation / click / type / select / verify actions
- Do NOT combine actions in one step
- Use ONLY the RAG context below

RAG CONTEXT:
{rag_context}
""".strip()

    # --- CALL LLM ---
    response = chat_completion([
        {"role": "user", "content": prompt}
    ])

    # --- PARSE JSON ---
    try:
        data = json.loads(response)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LLM did not return valid JSON:\n{response}") from e

    # --- BUILD TABLE ROWS (one row per step) ---
    rows = []
    sl = 1

    header = data.get("header", {})
    steps = data.get("steps", [])

    for step in steps:
        rows.append({
            "Sl No": sl,
            "Test Case ID": header.get("test_case_id", ""),
            "Jira Ref": header.get("jira_ref", ""),
            "Test Case Description": header.get("test_case_description", task),
            "Pre-requisites": ", ".join(header.get("pre_requisites", []) or []),
            "Test Data": ", ".join(header.get("test_data", []) or []),
            "Action": step.get("action", ""),
            "Expected Result": step.get("expected_result", ""),
            "Priority": header.get("priority", "High"),
        })
        sl += 1

    # Wrap into a single JSON output object (practical)
    final_output = {
        "test_cases": rows,
        "rag_topk_docs": [f"{r.get('doc')}#{r.get('chunk')}" for r in rag_results],
        "rag_context_len": len(rag_context),
    }
    return final_output


if __name__ == "__main__":
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print('Usage: python testcase_generate.py "Order cancellation"')
        sys.exit(1)

    task = sys.argv[1].strip()
    out = generate_testcase(task)
    print(json.dumps(out, indent=2))