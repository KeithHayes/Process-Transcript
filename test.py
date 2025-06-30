import asyncio
import logging
import os
import sys
import re
from pathlib import Path

# Add parent directory to path to allow imports from config and logger
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from process import ParseFile 
from logger import configure_logging
from config import CLEANED_FILE

configure_logging()
logger = logging.getLogger(__name__)

def diff_texts(original, processed):
    """Compare two texts word by word and show differences"""
    orig_words = original.split()
    proc_words = processed.split()
    
    differences = []
    for i, (ow, pw) in enumerate(zip(orig_words, proc_words)):
        if ow.lower() != pw.lower():
            differences.append(f"Position {i}: Original='{ow}' vs Processed='{pw}'")
    
    if len(orig_words) != len(proc_words):
        differences.append(f"Length mismatch: Original={len(orig_words)}, Processed={len(proc_words)}")
    
    return differences

async def main():
    async with ParseFile() as parser_instance:
        dummy_input_file = 'files/transcript.txt'
        test_failed = False

        try:
            # Ensure files directory exists
            os.makedirs('files', exist_ok=True)
            
            # Ensure transcript.txt exists for preprocess
            if not os.path.exists(dummy_input_file):
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

            # Format the chunk
            formatted_output = await parser_instance.formatchunk(first_250_words)

            # Verify formatting actually occurred
            if formatted_output == first_250_words:
                logger.error("Formatting failed - formattting failed")
                test_failed = True
            else:
                # Post-process
                deformatted_output = parser_instance.deformat(formatted_output)

                # Save outputs
                with open('files/unformattedtext.txt', 'w', encoding='utf-8') as f:
                    f.write(first_250_words)
                with open('files/deformattedtext.txt', 'w', encoding='utf-8') as f:
                    f.write(deformatted_output)

                # Compare word counts
                unformatted_word_count = len(first_250_words.split())
                deformatted_word_count = len(deformatted_output.split())
                
                if unformatted_word_count != deformatted_word_count:
                    logger.error(f"Word count mismatch. Original: {unformatted_word_count}, Deformatted: {deformatted_word_count}")
                    test_failed = True
                else:
                    logger.info("Word count matches")

                # Run detailed diff
                with open('files/unformattedtext.txt', 'r', encoding='utf-8') as f:
                    original = f.read()
                with open('files/deformattedtext.txt', 'r', encoding='utf-8') as f:
                    processed = f.read()
                
                diffs = diff_texts(original, processed)
                if diffs:
                    logger.error("Differences found:")
                    for diff in diffs:
                        logger.error(diff)
                    test_failed = True
                else:
                    logger.info("No differences found - words preserved perfectly")

                # Verify newlines were added
                if '\n' not in deformatted_output:
                    logger.error("No sentence breaks found in output")
                    test_failed = True

        except Exception as e:
            logger.error(f"Test failed: {str(e)}", exc_info=True)
            test_failed = True
            raise

        if test_failed:
            logger.error("TEST FAILED - One or more checks failed")
            sys.exit(1)
        else:
            logger.info("TEST PASSED - All checks completed successfully")
            sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())