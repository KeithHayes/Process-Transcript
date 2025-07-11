import re
import os

def get_text_chunk(filepath, index, size):
    """
    Extracts a chunk of text from a file, preserving original formatting,
    starting from the word pointed to by 'index'.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()

    except Exception as e:
        return f"Error reading file: {e}"
    
    matches = list(re.finditer(r'\S+', text))
    if index > len(matches):
        return ""

    remainder = len(matches) - index
    if (remainder < size):
        size = remainder

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

    # Write chunk to file
    chunk = get_text_chunk('files/desired_output.txt', 0, 200)
    deformatted = preprocess(chunk)
    with open("chunk_document/output_chunk_1.txt", "w", encoding='utf-8') as f:
        f.write(chunk)
    with open("chunk_document/input_chunk_1.txt", "w", encoding='utf-8') as f:
        f.write(deformatted)


    chunk = get_text_chunk('files/desired_output.txt', 125, 200)
    deformatted = preprocess(chunk)
    with open("chunk_document/output_chunk_2.txt", "w", encoding='utf-8') as f:
        f.write(chunk)
    with open("chunk_document/input_chunk_2.txt", "w", encoding='utf-8') as f:
        f.write(deformatted)

    chunk = get_text_chunk('files/desired_output.txt', 250, 200)
    deformatted = preprocess(chunk)
    with open("chunk_document/output_chunk_3.txt", "w", encoding='utf-8') as f:
        f.write(chunk)
    with open("chunk_document/input_chunk_3.txt", "w", encoding='utf-8') as f:
        f.write(deformatted)


    chunk = get_text_chunk('files/desired_output.txt', 375, 200)
    deformatted = preprocess(chunk)
    with open("chunk_document/output_chunk_4.txt", "w", encoding='utf-8') as f:
        f.write(chunk)
    with open("chunk_document/input_chunk_4.txt", "w", encoding='utf-8') as f:
        f.write(deformatted)

    chunk = get_text_chunk('files/desired_output.txt', 500, 200)
    deformatted = preprocess(chunk)
    with open("chunk_document/output_chunk_5.txt", "w", encoding='utf-8') as f:
        f.write(chunk)
    with open("chunk_document/input_chunk_5.txt", "w", encoding='utf-8') as f:
        f.write(deformatted)


    chunk = get_text_chunk('files/desired_output.txt', 625, 200)
    deformatted = preprocess(chunk)
    with open("chunk_document/output_chunk_6.txt", "w", encoding='utf-8') as f:
        f.write(chunk)
    with open("chunk_document/input_chunk_6.txt", "w", encoding='utf-8') as f:
        f.write(deformatted)

    chunk = get_text_chunk('files/desired_output.txt', 750, 200)
    deformatted = preprocess(chunk)
    with open("chunk_document/output_chunk_7.txt", "w", encoding='utf-8') as f:
        f.write(chunk)
    with open("chunk_document/input_chunk_7.txt", "w", encoding='utf-8') as f:
        f.write(deformatted)


    chunk = get_text_chunk('files/desired_output.txt', 875, 200)
    deformatted = preprocess(chunk)
    with open("chunk_document/output_chunk_8.txt", "w", encoding='utf-8') as f:
        f.write(chunk)
    with open("chunk_document/input_chunk_8.txt", "w", encoding='utf-8') as f:
        f.write(deformatted)


    # Test output
    print("Sample chunks written")



