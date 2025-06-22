import requests

url = "http://0.0.0.0:5000/v1/completions"
payload = {
    "model": "TheBloke_Mistral-7B-Instruct-v0.2-AWQ",
    "prompt": "[INST] What is the capital of France? [/INST]",
    "max_tokens": 20
}

response = requests.post(url, json=payload)
print("Status Code:", response.status_code)
print("Response:", response.json())