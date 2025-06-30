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
        # ... [previous setup code remains the same]

        with open(preprocessed_file_path, 'r', encoding='utf-8') as f:
            full_text = f.read()
            words = full_text.split()
            first_250_words = ' '.join(words[:250])

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
        with open('files/unformattedtext.txt', 'w') as f:
            f.write(first_250_words)
        with open('files/deformattedtext.txt', 'w') as f:
            f.write(deformatted_output)

        # Calculate expected length increase
        newline_count = deformatted_output.count('\n')
        expected_length = len(first_250_words) + newline_count
        
        if len(deformatted_output) != expected_length:
            logger.error(f"Length mismatch. Expected {expected_length}, got {len(deformatted_output)}")
        else:
            logger.info("Output length matches expectations")

if __name__ == "__main__":
    asyncio.run(main())