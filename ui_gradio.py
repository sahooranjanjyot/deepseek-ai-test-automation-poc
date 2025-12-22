import os
import traceback

import gradio as gr
from dotenv import load_dotenv

# Use your existing pipeline (same as llm_generate.py)
from tools.llm.local_client import chat_completion

# ----------------------------
# Load .env.local (hard bind)
# ----------------------------
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env.local")
load_dotenv(ENV_PATH, override=True)

BASE_URL = (os.getenv("LOCAL_LLM_BASE_URL") or "").strip()
API_KEY = (os.getenv("LOCAL_LLM_API_KEY") or "").strip()
MODEL = (os.getenv("LOCAL_LLM_MODEL") or "").strip()

def _status_text() -> str:
    lines = []
    lines.append(f"Connected to:\n{BASE_URL or '(missing LOCAL_LLM_BASE_URL)'}\n")
    lines.append(f"API key set: {'YES' if bool(API_KEY) else 'NO'}")
    lines.append(f"Env model: {MODEL or '(missing LOCAL_LLM_MODEL)'}")
    lines.append(f"Loaded from: {ENV_PATH}")
    return "\n".join(lines)

def generate_ui(user_prompt: str, temperature: float, max_tokens: int) -> str:
    # NOTE: We intentionally do NOT pass model/messages kwargs,
    # because your tools/llm/local_client.py chat_completion() expects only (task/user_prompt).
    if not user_prompt or not user_prompt.strip():
        return "ERROR: Please enter a prompt."

    try:
        # Your local_client should read BASE_URL/API_KEY/MODEL from env
        # and will hit /v1/chat/completions or /v1/completions internally.
        out = chat_completion(user_prompt.strip())
        return out
    except Exception as e:
        return (
            "ERROR while calling model:\n"
            + f"{type(e).__name__}: {e}\n\n"
            + traceback.format_exc()
        )

with gr.Blocks(title="DeepSeek vLLM UI (RunPod / Local)") as demo:
    gr.Markdown("# DeepSeek vLLM UI (RunPod / Local)")
    gr.Markdown("Plain English → model output.")
    gr.Markdown("Uses your existing `tools/llm/local_client.py` (same pipeline as `llm_generate.py`).")
    gr.Markdown("Model is hard-bound from `.env.local` (no discovery, no dropdown).")

    model_box = gr.Textbox(
        label="Model (from .env.local)",
        value=MODEL,
        interactive=False
    )

    status_box = gr.Textbox(
        label="Status",
        value=_status_text(),
        lines=5,
        interactive=False
    )

    prompt = gr.Textbox(
        label="Your request (plain English)",
        placeholder='e.g., "Generate a Gherkin scenario for canceling a pending order."',
        lines=4
    )

    temperature = gr.Slider(0, 1, value=0.0, step=0.05, label="Temperature")
    max_tokens = gr.Slider(64, 2048, value=512, step=32, label="Max tokens")

    btn = gr.Button("Generate", variant="primary")
    output = gr.Textbox(label="Model output", lines=18)

    btn.click(
        fn=generate_ui,
        inputs=[prompt, temperature, max_tokens],
        outputs=[output],
    )

if __name__ == "__main__":
    # run locally
    demo.launch(server_name="127.0.0.1", server_port=7860)