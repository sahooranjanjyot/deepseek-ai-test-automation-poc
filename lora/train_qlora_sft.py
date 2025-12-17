import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TrainingArguments
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer

BASE_MODEL = "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
DATA_FILE = "lora/data/train.jsonl"
OUTPUT_DIR = "lora/out/adapter"

def formatting_func(example):
    return example["text"]

def main():
    dataset = load_dataset(
        "json",
        data_files=DATA_FILE,
        split="train"
    )

    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL,
        trust_remote_code=True
    )
    tokenizer.pad_token = tokenizer.eos_token

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]
    )

    model = get_peft_model(model, lora_config)

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        num_train_epochs=3,
        logging_steps=5,
        save_strategy="epoch",
        bf16=True,
        optim="paged_adamw_8bit",
        report_to="none"
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        formatting_func=formatting_func,
        args=training_args
    )

    trainer.train()
    trainer.save_model(OUTPUT_DIR)

if __name__ == "__main__":
    main()
