import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

BASE_MODEL = "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
ADAPTER_PATH = "lora/out/adapter"

PROMPT = """You are a QA test case generator.
Return ONLY valid JSON. No markdown. No explanation.

Schema:
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
"""

def extract_json(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON found in output")
    return text[start:end + 1]

def main():
    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL,
        trust_remote_code=True
    )

    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        device_map="auto",
        load_in_8bit=True,          # 🔥 KEY FIX
        trust_remote_code=True
    )

    model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
    model.eval()

    inputs = tokenizer(PROMPT, return_tensors="pt").to(model.device)

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=400,
            do_sample=False
        )

    text = tokenizer.decode(output[0], skip_special_tokens=True)
    json_text = extract_json(text)
    parsed = json.loads(json_text)

    print(json.dumps(parsed, indent=2))

if __name__ == "__main__":
    main()
