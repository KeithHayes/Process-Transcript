import asyncio
import logging
import os
import sys
import re

# Add parent directory to path to allow imports from config and logger
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from process import ParseFile 
from logger import configure_logging
from config import CLEANED_FILE

configure_logging()
logger = logging.getLogger(__name__)

async def main():
    async with ParseFile() as parser_instance:
        dummy_input_file = 'files/transcript.txt'

        try:
            # Ensure transcript.txt exists for preprocess
            if not os.path.exists(dummy_input_file):
                os.makedirs(os.path.dirname(dummy_input_file) or '.', exist_ok=True)
                with open(dummy_input_file, 'w', encoding='utf-8') as f:
                    f.write("This is a test sentence. This is another one. This helps preprocess create the file.")
                logger.info(f"Created a dummy '{dummy_input_file}' for preprocessing.")

            parser_instance.preprocess(dummy_input_file)

            with open(CLEANED_FILE, 'r', encoding='utf-8') as f:
                full_text = f.read()
                words = full_text.split()
                first_250_words = ' '.join(words[:250])

            logger.info(f"Loaded first {len(words[:250])} words from '{CLEANED_FILE}'.")
            logger.debug(f"Input text for formatchunk: '{first_250_words[:100]}...'")

            original_words = first_250_words.split()
            
            # Format the chunk
            formatted_output = await parser_instance.formatchunk(first_250_words)
            
            # Verify no words were changed
            formatted_words = re.sub(r'[.!?,;]', '', formatted_output).split()
            if original_words != formatted_words:
                logger.error("Word mismatch between original and formatted text")
                for i, (orig, fmt) in enumerate(zip(original_words, formatted_words)):
                    if orig != fmt:
                        logger.error(f"Difference at word {i}: Original='{orig}' vs Formatted='{fmt}'")

            # Post-process
            deformatted_output = parser_instance.deformat(formatted_output)
            
            # Verify word count and order
            deformatted_words = deformatted_output.split()
            if len(original_words) != len(deformatted_words):
                logger.error("Word count changed during processing")
            elif original_words != deformatted_words:
                logger.error("Word order changed during processing")

            # Save outputs
            os.makedirs('files', exist_ok=True)
            with open('files/unformattedtext.txt', 'w', encoding='utf-8') as f:
                f.write(first_250_words)
            with open('files/deformattedtext.txt', 'w', encoding='utf-8') as f:
                f.write(deformatted_output)

            # Calculate expected length increase
            newline_count = deformatted_output.count('\n')
            expected_length = len(first_250_words) + newline_count
            
            if len(deformatted_output) != expected_length:
                logger.error(f"Length mismatch. Expected {expected_length}, got {len(deformatted_output)}")
            else:
                logger.info("Output length matches expectations")

            logger.info("Saved 'unformattedtext.txt' and 'deformattedtext.txt' successfully.")

        except Exception as e:
            logger.error(f"Test failed: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())