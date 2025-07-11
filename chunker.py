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
    text = text.replace("—", " -- ")
    text = re.sub(r"[^A-Za-z0-9'\-]+", " ", text)
    text = re.sub(r'\s+', ' ', text).strip()
    words = [word for word in text.split(' ') if word]
    cleaned_text = ' '.join(words)
    return cleaned_text


if __name__ == "__main__":
    os.makedirs("chunk_document", exist_ok=True)
    with open('files/desired_output.txt', 'r', encoding='utf-8') as f:
        text = f.read()
        matches = list(re.finditer(r'\S+', text))

    chunk_size = 200
    start_indices = range(0, len(matches), 125) 

    for i, start_index in enumerate(start_indices):
        chunk_number = i + 1
        chunk = get_text_chunk('files/desired_output.txt', start_index, chunk_size)
        
        if chunk and not chunk.startswith("Error"):
            deformatted = preprocess(chunk)
            
            output_filename = f"chunk_document/output_chunk_{chunk_number}.txt"
            input_filename = f"chunk_document/input_chunk_{chunk_number}.txt"

            with open(output_filename, "w", encoding='utf-8') as f:
                f.write(chunk)
            with open(input_filename, "w", encoding='utf-8') as f:
                f.write(deformatted)
        elif chunk.startswith("Error"):
            print(f"Skipping chunk {chunk_number} due to error: {chunk}")
        else:
            print(f"Skipping chunk {chunk_number} as no text was extracted from index {start_index}.")


    # word count
    print(f"Sample chunks written, word count = {len(matches)}")