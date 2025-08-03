import re
import os
from config import DESIRED_OUTPUT

def process_transcript(input_file):
    # Read the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Step 1: Replace newlines with a special character (using a non-whitespace control character)
    special_char = '\x1E'  # Using INFORMATION SEPARATOR TWO (U+001E) as our special character
    text = text.replace('\n', special_char)
    
    # Step 2: Replace all whitespace (except our special char) with single space
    # We'll first protect our special character during whitespace normalization
    protected_text = []
    for char in text:
        if char == special_char:
            protected_text.append(special_char)
        elif char.isspace():
            protected_text.append(' ')
        else:
            protected_text.append(char)
    text = ''.join(protected_text)
    
    # Step 3: Remove all punctuation (keeping alphanumeric and our special char)
    text = re.sub(fr'[^\w\s{re.escape(special_char)}]', '', text)
    
    # Step 4: Convert to lowercase (excluding our special char)
    processed_text = []
    for char in text:
        if char == special_char:
            processed_text.append(char)
        else:
            processed_text.append(char.lower())
    text = ''.join(processed_text)
    
    # Step 5: Replace newlines (special character) with spaces
    text = text.replace(special_char, ' ')
    
    # Create output filename
    base_name = os.path.basename(input_file)
    if 'formatted' in base_name:
        output_name = base_name.replace('formatted', '')
    else:
        output_name = os.path.splitext(base_name)[0] + '.txt'
    
    # Write to output file
    output_path = os.path.join('files', output_name)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    return output_path

if __name__ == "__main__":
    # Process the desired output file
    input_file = os.path.join('files', DESIRED_OUTPUT)
    output_file = process_transcript(input_file)
    print(f"Processed file saved to: {output_file}")