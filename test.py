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

async def main():
    # Instantiate ParseFile, which initializes self.session and self.logger
    # Use it as an async context manager to ensure the session is properly closed
    async with ParseFile() as parser_instance: 
        preprocessed_file_path = CLEANED_FILE # Use CLEANED_FILE from config
        
        # Ensure the preprocessed file exists and has content for testing
        try:
            # First, run preprocess to ensure CLEANED_FILE exists
            # This is crucial because test.py might run without a full run.py execution.
            # We'll create a dummy 'transcript.txt' if it doesn't exist for preprocess.
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

        except FileNotFoundError:
            logger.error(f"Error: '{preprocessed_file_path}' not found even after preprocessing attempt. Please ensure file paths are correct.")
            return
        except Exception as e:
            logger.error(f"Error reading or preprocessing '{preprocessed_file_path}': {e}")
            return

        logger.info("Calling formatchunk with the extracted text...")
        # Call the formatchunk method on the parser_instance
        formatted_output_from_llm = await parser_instance.formatchunk(first_250_words)

        logger.info("\n--- LLM's Raw Formatted Output (single-space separated sentences) ---")
        logger.info(formatted_output_from_llm) 
        logger.info("--- End LLM's Raw Formatted Output ---\n")

        # --- POST-PROCESSING STEP: Adding newlines for display ---
        logger.info("\n--- Post-Processed Output (each sentence on new line) ---")
        # Regex to split by sentence-ending punctuation followed by a space
        # (?<=[.!?]) is a positive lookbehind assertion, ensuring the split happens AFTER the punctuation
        sentences = re.split(r'(?<=[.!?])\s+', formatted_output_from_llm)
        # Filter out any empty strings that might result from the split and strip whitespace
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Join with newlines
        post_processed_output = "\n".join(sentences)
        logger.info(post_processed_output)
        logger.info("--- End Post-Processed Output ---\n")
        # --- END POST-PROCESSING STEP ---

if __name__ == "__main__":
    asyncio.run(main())