import asyncio
import logging
import os
import sys
import re

# Add parent directory to path to allow imports from config and logger
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

from process import ParseFile 
from logger import configure_logging
from config import CLEANED_FILE

configure_logging()
logger = logging.getLogger(__name__)

def deformatchunk(formatted_output):
    # Only split sentences, don't remove punctuation
    split_output = re.sub(r'(?<=[.!?])\s+(?=[A-Z])', '\n', formatted_output)
    # Just normalize whitespace
    cleaned_output = re.sub(r'\s{2,}', ' ', split_output)
    cleaned_output = re.sub(r'\s*$', ' ', cleaned_output)
    return cleaned_output

async def main():
    async with ParseFile() as parser_instance:
        preprocessed_file_path = CLEANED_FILE
        dummy_input_file = 'files/transcript.txt'

        try:
            # Ensure transcript.txt exists for preprocess
            if not os.path.exists(dummy_input_file):
                os.makedirs(os.path.dirname(dummy_input_file) or '.', exist_ok=True)
                with open(dummy_input_file, 'w', encoding='utf-8') as f:
                    f.write("This is a test sentence. This is another one. This helps preprocess create the file.")
                logger.info(f"Created a dummy '{dummy_input_file}' for preprocessing.")

            parser_instance.preprocess(dummy_input_file)

            with open(preprocessed_file_path, 'r', encoding='utf-8') as f:
                full_text = f.read()
                words = full_text.split()
                first_250_words = ' '.join(words[:250])

            logger.info(f"Loaded first {len(words[:250])} words from '{preprocessed_file_path}'.")
            logger.debug(f"Input text for formatchunk: '{first_250_words[:100]}...'")

            logger.info("Calling formatchunk with the extracted text...")
            unformatted_length = len(first_250_words)

            # Format the chunk
            formatted_output = await parser_instance.formatchunk(first_250_words)

            # Post-process
            deformatted_output = deformatchunk(formatted_output)
            deformatted_length = len(deformatted_output)

            # Save outputs
            os.makedirs('files', exist_ok=True)
            with open('files/unformattedtext.txt', 'w', encoding='utf-8') as f:
                f.write(first_250_words)
            with open('files/deformattedtext.txt', 'w', encoding='utf-8') as f:
                f.write(deformatted_output)

            # Compare word counts instead of exact lengths since formatting changes punctuation
            unformatted_word_count = len(first_250_words.split())
            deformatted_word_count = len(deformatted_output.split())
            
            if unformatted_word_count != deformatted_word_count:
                logger.error(
                    f"Error: Word count mismatch. Original: {unformatted_word_count}, "
                    f"Deformatted: {deformatted_word_count}"
                )
            else:
                logger.info("Word count match check passed.")
                logger.info(f"Original length: {unformatted_length}, Formatted length: {len(formatted_output)}, Deformatted length: {deformatted_length}")

            logger.info("Saved 'unformattedtext.txt' and 'deformattedtext.txt' successfully.")

        except Exception as e:
            logger.error(f"Test failed: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())