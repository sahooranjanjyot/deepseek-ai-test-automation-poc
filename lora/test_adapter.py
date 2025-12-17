import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

BASE_MODEL = "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
ADAPTER_PATH = "lora/out/adapter"

PROMPT = """
You are a QA test case generator.
Return ONLY valid JSON. No markdown. No explanations.
Output must be a SINGLE JSON object.

JSON schema:
{
  "test_cases": [
    {
      "sl_no": 1,
      "test_case_id": "TC001",
      "jira_ref": "JIRA-123",
      "description": "",
      "preconditions": [],
      "test_data": [],
      "steps": [
        { "action": "", "expected_result": "" }
      ],
      "priority": "High"
    }
  ]
}

Task: Order cancellation.
Scenario: User wants to cancel an order.
""".strip()


def extract_first_json(text: str) -> str:
    """
    Extract the first top-level JSON object { ... } from a noisy model output.
    This avoids JSONDecodeError: Extra data.
    """
    start = text.find("{")
    if start == -1:
        raise ValueError("No '{' found in model output.")

    depth = 0
    in_str = False
    esc = False

    for i in range(start, len(text)):
        ch = text[i]

        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        else:
            if ch == '"':
                in_str = True
                continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    raise ValueError("Unbalanced JSON braces in output.")


def main():
    # Avoid transformers importing torchvision stuff
    # (export TRANSFORMERS_NO_TORCHVISION=1 is still recommended in shell)
    device_map = "auto"
    dtype = torch.float16

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)

    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        trust_remote_code=True,
        torch_dtype=dtype,
        device_map=device_map,
    )

    model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
    model.eval()

    inputs = tokenizer(PROMPT, return_tensors="pt")
    inputs = {k: v.to(model.device) for k, v in inputs.items()}

    # ✅ The important fix:
    # - do_sample=False (deterministic)
    # - use_cache=False (avoids DynamicCache/seen_tokens crash you hit)
    with torch.no_grad():
        outputs = model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs.get("attention_mask", None),
            max_new_tokens=512,
            do_sample=False,
            use_cache=False,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    raw = tokenizer.decode(outputs[0], skip_special_tokens=True)

    json_text = extract_first_json(raw)
    parsed = json.loads(json_text)

    print(json.dumps(parsed, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
