import os
import argparse
import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--model",
        default=os.getenv(
            "LOCAL_LLM_MODEL",
            "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
        ),
    )
    ap.add_argument("--train", default="lora/data/train.jsonl")
    ap.add_argument("--eval", default="lora/data/eval.jsonl")
    ap.add_argument("--out", default="lora/out/adapter")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--bs", type=int, default=1)
    ap.add_argument("--ga", type=int, default=16)
    ap.add_argument("--max_len", type=int, default=2048)
    args = ap.parse_args()

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    tokenizer = AutoTokenizer.from_pretrained(
        args.model, use_fast=True, trust_remote_code=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        attn_implementation="eager",  # flash-attn disabled
    )

    model = prepare_model_for_kbit_training(model)

    lora_cfg = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )

    model = get_peft_model(model, lora_cfg)

    data_files = {"train": args.train}
    if os.path.exists(args.eval):
        data_files["eval"] = args.eval

    ds = load_dataset("json", data_files=data_files)

    def to_text(example):
        return {
            "text": (
                example["prompt"].strip()
                + "\n\n### RESPONSE_JSON\n"
                + example["response"].strip()
                + tokenizer.eos_token
            )
        }

    ds = ds.map(to_text, remove_columns=ds["train"].column_names)

    training_args = TrainingArguments(
        output_dir=args.out,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.bs,
        gradient_accumulation_steps=args.ga,
        learning_rate=args.lr,
        bf16=True,
        logging_steps=10,
        save_steps=200,
        save_total_limit=2,
        evaluation_strategy="no",
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=ds["train"],
        dataset_text_field="text",
        max_seq_length=args.max_len,
        args=training_args,
    )

    trainer.train()

    os.makedirs(args.out, exist_ok=True)
    trainer.model.save_pretrained(args.out)
    tokenizer.save_pretrained(args.out)

    print(f"Saved LoRA adapter to: {args.out}")


if __name__ == "__main__":
    main()
