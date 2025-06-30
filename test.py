import asyncio
import logging
import os
import sys
import re # Import re for post-processing demonstration

# Add parent directory to path to allow imports from config and logger
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the ParseFile class from process.py
from process import ParseFile 
from logger import configure_logging
from config import CLEANED_FILE # Import CLEANED_FILE from config

configure_logging()
logger = logging.getLogger(__name__)

def deformatchunk(formatted_output):
    split_output = re.sub(r'(?<=[.!?])\s+(?=[A-Z])', '\n', formatted_output)
    cleaned_output = re.sub(r'[.!?,;-]', '', split_output)
    cleaned_output = re.sub(r'\s{2,}', ' ', cleaned_output)
    cleaned_output = re.sub(r'\s*$', ' ', cleaned_output)
    return cleaned_output

async def main():
    async with ParseFile() as parser_instance: 
        preprocessed_file_path = CLEANED_FILE 
        
        try:
            dummy_input_file = 'files/transcript.txt'
            if not os.path.exists(dummy_input_file):
                os.makedirs(os.path.dirname(dummy_input_file) or '.', exist_ok=True)
                with open(dummy_input_file, 'w', encoding='utf-8') as f:
                    f.write("This is a test sentence. This is another one. This helps preprocess create the file.")
                logger.info(f"Created a dummy '{dummy_input_file}' for preprocessing.")

            parser_instance.preprocess(dummy_input_file) # Ensure CLEANED_FILE is created/updated
            
            with open(preprocessed_file_path, 'r', encoding='utf-8') as f:
                full_text = f.read()
                words = full_text.split()
                # Take the first 250 words, or all words if fewer than 250
                first_250_words = ' '.join(words[:250])
            logger.info(f"Loaded first {len(words[:250])} words from '{preprocessed_file_path}'.")
            logger.debug(f"Input text for formatchunk: '{first_250_words[:100]}...'")

        logger.info("Calling formatchunk with the extracted text...")

        unformatted_length = len(first_250_words)
        # Call the formatchunk method on the parser_instance
        formatted_output = await parser_instance.formatchunk(first_250_words)


        deformatted_output = deformatchunk(formatted_output)
        deformatted_length = len(deformatted_output)

        if((unformatted_length + deformatted_output.count('\n')) != deformatted_length):
            logger.error(f"{ unformatted_length + deformatted_output.count - deformatted_length }Error: Length mismatch.")



        # save the unformatted text to files/unformattedtext.txt
        # save the deformatted_output text to files/deformattedtext.txt



        # --- END POST-PROCESSING STEP ---

if __name__ == "__main__":
    asyncio.run(main())