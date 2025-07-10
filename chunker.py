import re
import os

def get_text_chunk(filepath, index, size):
    """
    Extracts a chunk of text from a file, preserving original formatting,
    starting from the `index`-th word for a total of `size` words.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()




    except Exception as e:
        return f"Error reading file: {e}"

    matches = list(re.finditer(r'\S+', text))
    if index < 0 or index + size > len(matches):
        return ""

    start = matches[index].start()
    end = matches[index + size - 1].end()
    return text[start:end]

def preprocess(text):
    text = text.lower()
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')
    text = text.replace("—", " -- ") # Normalize em-dashes to spaces
    text = re.sub(r"[^A-Za-z0-9'\-]+", " ", text)
    text = re.sub(r'\s+', ' ', text).strip()
    words = [word for word in text.split(' ') if word]
    cleaned_text = ' '.join(words)
    return cleaned_text


if __name__ == "__main__":
    # Ensure output directory exists
    os.makedirs("chunk_document", exist_ok=True)

    # Test output
    print(f"Test 1: {get_text_chunk('files/desired_output.txt', 25, 5)}")

    # Write chunk to file
    chunk = get_text_chunk('files/desired_output.txt', 0, 200)

    with open("chunk_document/output_chunk_1.txt", "w", encoding='utf-8') as f:
        f.write(chunk)

    # deformat the chunk
    deformatted = preprocess(chunk)

    with open("chunk_document/input_chunk_1.txt", "w", encoding='utf-8') as f:
        f.write(deformatted)

