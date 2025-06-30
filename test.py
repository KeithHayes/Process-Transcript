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
    # [previous setup code...]
    
    try:
        # [previous processing code...]
        
        # After saving files, run diff
        with open('files/unformattedtext.txt', 'r') as f:
            original = f.read()
        with open('files/deformattedtext.txt', 'r') as f:
            processed = f.read()
            
        diffs = diff_texts(original, processed)
        if diffs:
            logger.error("Differences found:")
            for diff in diffs:
                logger.error(diff)
        else:
            logger.info("No differences found - words preserved perfectly")
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())