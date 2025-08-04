#!/usr/bin/env python3
import requests
import json

API_URL = "http://localhost:5000/v1/completions"
HEADERS = {"Content-Type": "application/json"}

def generate_punctuation(text):
    """Generate properly punctuated text using the API with the exact training prompt format"""
    prompt = f"Punctuate sentences. {text}"
    
    payload = {
        "prompt": prompt,
        "max_tokens": 100,
        "temperature": 0.3,  # Lower for more predictable punctuation
        "top_p": 0.9,
        "repetition_penalty": 1.1,
        "stop": ["\n"]  # Stop at newlines to get just one sentence
    }
    
    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        result = response.json()
        
        # The full response will be "Punctuate sentences. [original] [punctuated]"
        # So we need to extract just the punctuated part
        full_response = result['choices'][0]['text']
        
        # Remove the prompt prefix and original text
        if full_response.startswith(f"Punctuate sentences. {text}"):
            punctuated = full_response[len(f"Punctuate sentences. {text}"):].strip()
        else:
            punctuated = full_response.strip()
            
        return punctuated
    
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    test_cases = [
        "i cant believe its not butter",
        "the meeting is at 3pm tomorrow dont forget",
        "she said im going to the store then ill be back",
        "having trouble with my computer its very slow and keeps freezing",
        "we went to paris france and rome italy last summer",
        "alice warren sat beside a wide window in the corner of her study",
        "the late afternoon light slanted gently across the hardwood floor illuminating endless rows of books that lined the walls",
        "she loved the hush of quiet contemplation the soft rustle of turning pages and the subtle comfort of stories held within paper and ink",
        "it was in this exact space that she found solace after a long day of meetings presentations and endless email chains",
        "the silence was not merely an absence of noise it was a presence in itself a companion that whispered in comfortable tones and allowed thoughts to drift unencumbered"
    ]
    
    print("\nTesting punctuation via API:")
    print("-" * 60)
    
    for text in test_cases:
        print(f"\nOriginal: {text}")
        corrected = generate_punctuation(text)
        print(f"Corrected: {corrected}")
        print("-" * 60)

if __name__ == "__main__":
    main()