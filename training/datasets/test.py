#!/usr/bin/env python3
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

def load_model_and_tokenizer():
    """Load the base model, adapter, and tokenizer"""
    print("Loading model and tokenizer...")
    
    # Load base model
    base_model = AutoModelForCausalLM.from_pretrained(
        "/media/external_drive1/ai/textdata/models/TinyLlama-1.1B-Chat-v1.0",
        device_map="auto",
        torch_dtype=torch.float16
    )
    
    # Load fine-tuned adapter
    model = PeftModel.from_pretrained(
        base_model,
        "/home/kdog/text-generation-webui/training/trained_checkpoints/tinyllama_punctuation"
    )
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        "/media/external_drive1/ai/textdata/models/TinyLlama-1.1B-Chat-v1.0"
    )
    
    return model, tokenizer

def generate_punctuation(model, tokenizer, text):
    """Generate punctuated text"""
    prompt = (
        "Below is an instruction that describes a task. Write a response that appropriately completes the request.\n\n"
        "### Instruction:\n"
        "Punctuate this text:\n\n"
        f"### Input:\n{text}\n\n"
        "### Response:"
    )
    
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=100,
            do_sample=True,
            temperature=0.7,
            top_p=0.9
        )
    
    full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # Extract just the response part after "### Response:"
    response = full_response.split("### Response:")[-1].strip()
    return response

def main():
    # Initialize model
    model, tokenizer = load_model_and_tokenizer()
    
    # Test cases
    test_cases = [
        "i cant believe its not butter",
        "the meeting is at 3pm tomorrow dont forget",
        "she said im going to the store then ill be back",
        "having trouble with my computer its very slow and keeps freezing",
        "we went to paris france and rome italy last summer"
    ]
    
    print("\nTesting punctuation model:")
    print("-" * 50)
    
    for text in test_cases:
        print(f"\nOriginal: {text}")
        punctuated = generate_punctuation(model, tokenizer, text)
        print(f"Corrected: {punctuated}")
        print("-" * 50)

if __name__ == "__main__":
    main()