# cag_script.py
# Single-run CLI CAG using IBM Granite 2B

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from transformers.cache_utils import DynamicCache
from torch.serialization import add_safe_globals
import os
import argparse

MODEL_NAME = "ibm-granite/granite-3.1-2b-instruct"
KNOWLEDGE_FILE = "./data/knowledge_library/knowledge.txt"
CACHE_FILE = "./data/knowledge_library/knowledge.pt"

# Quantisierung konfigurieren
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)

# Modell und Tokenizer laden
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True
)

def preprocess_knowledge(knowledge: str) -> DynamicCache:
    prompt = f"""
    Documents:
    {knowledge.strip()}
    Instruction:
    Answer the question:
    """
    input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to(model.device)
    kv_cache = DynamicCache()
    with torch.no_grad():
        _ = model(
            input_ids=input_ids,
            past_key_values=kv_cache,
            use_cache=True
        )
    return kv_cache, kv_cache.key_cache[0].shape[-2]

def save_cache(kv_cache: DynamicCache, path: str):
    torch.save(kv_cache, path)

def load_cache(path: str) -> DynamicCache:
    add_safe_globals([DynamicCache])  # wichtig!
    return torch.load(path, weights_only=False)

def clean_up_cache(kv_cache: DynamicCache, origin_len: int):
    for i in range(len(kv_cache.key_cache)):
        kv_cache.key_cache[i] = kv_cache.key_cache[i][:, :, :origin_len, :]
        kv_cache.value_cache[i] = kv_cache.value_cache[i][:, :, :origin_len, :]

def generate_answer(question: str, kv_cache: DynamicCache, kv_len: int):
    clean_up_cache(kv_cache, kv_len)
    input_ids = tokenizer(question, return_tensors="pt").input_ids.to(model.device)

    output_ids = input_ids.clone()
    next_token = input_ids

    with torch.no_grad():
        for _ in range(300):
            output = model(
                input_ids=next_token,
                past_key_values=kv_cache,
                use_cache=True
            )
            logits = output.logits[:, -1, :]
            next_token = logits.argmax(dim=-1).unsqueeze(-1)
            kv_cache = output.past_key_values
            output_ids = torch.cat([output_ids, next_token], dim=1)
            if next_token.item() == tokenizer.eos_token_id:
                break

    return tokenizer.decode(output_ids[0], skip_special_tokens=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", type=str, required=True, help="Frage, die beantwortet werden soll")
    args = parser.parse_args()

    if not os.path.exists(CACHE_FILE):
        print("\n[Init] Erzeuge Cache aus knowledge.txt...")
        if not os.path.exists(KNOWLEDGE_FILE):
            raise FileNotFoundError(f"{KNOWLEDGE_FILE} nicht gefunden.")
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            knowledge = f.read()
        kv_cache, kv_len = preprocess_knowledge(knowledge)
        save_cache(kv_cache, CACHE_FILE)
        print("[Init] Cache gespeichert unter:", CACHE_FILE)
    else:
        print("\n[Load] Lade bestehenden Cache")
        kv_cache = load_cache(CACHE_FILE)
        kv_len = kv_cache.key_cache[0].shape[-2]

    print("\n[Frage]", args.question)
    answer = generate_answer(args.question, kv_cache, kv_len)
    print("\n[Antwort]", answer)

if __name__ == "__main__":
    main()
