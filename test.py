import re
import logging
from config import CLEANED_FILE

logger = logging.getLogger('processor_test')

def clean_llm_output(llm_output, original_text):
    """
    Revert unwanted LLM modifications while preserving newlines
    1. Restore original capitalization
    2. Remove added punctuation
    3. Preserve newlines between sentences
    """
    # Split both texts into words
    original_words = original_text.split()
    llm_words = llm_output.replace('\n', ' ').split()
    
    # Reconstruct text with original words but LLM newlines
    clean_lines = []
    original_index = 0
    
    for line in llm_output.split('\n'):
        line_words = line.split()
        line_length = len(line_words)
        
        # Get corresponding original words
        original_segment = original_words[original_index:original_index+line_length]
        clean_lines.append(' '.join(original_segment))
        original_index += line_length
    
    return '\n'.join(clean_lines)

def test_post_processor():
    """Test the post-processing cleanup"""
    with open(CLEANED_FILE, 'r') as f:
        original_text = ' '.join(f.read().split()[:50])
    
    # Simulate LLM output with unwanted changes
    llm_output = """alice warren sat beside a wide window in the corner of her study. The late afternoon light slanted gently across the hardwood floor, illuminating endless rows of books that lined the walls. She loved the"""
    
    cleaned = clean_llm_output(llm_output, original_text)
    
    # Verify
    if cleaned.replace('\n', ' ') != original_text:
        logger.error("Post-processing failed to restore original text")
        return False
    
    if '\n' not in cleaned:
        logger.error("Post-processing removed all newlines")
        return False
    
    logger.info("Post-processing successfully cleaned LLM output")
    return True

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Testing post-processor...")
    if test_post_processor():
        logger.info("SUCCESS: Post-processor works correctly")
    else:
        logger.error("FAILURE: Post-processor needs fixes")