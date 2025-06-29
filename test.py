import re
import logging
from pathlib import Path
from config import CLEANED_FILE

logger = logging.getLogger('sentence_test')

def count_words(text):
    """Count words in text (split on whitespace)"""
    return len(text.split()) if text.strip() else 0

def identify_sentences(text):
    """
    Identify sentence boundaries and replace spaces with newlines.
    Returns formatted text and original word count for verification.
    """
    # Basic sentence boundary detection (period followed by space and capital letter)
    sentence_pattern = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
    
    # Split into sentences
    sentences = re.split(sentence_pattern, text)
    
    # Join with newlines and ensure proper spacing
    formatted_text = '\n'.join(s.strip() for s in sentences if s.strip())
    
    return formatted_text, count_words(text)

def test_sentence_formatting():
    """Test sentence identification and formatting in first 250 words"""
    try:
        # Load preprocessed text
        with open(CLEANED_FILE, 'r', encoding='utf-8') as f:
            full_text = f.read()
        
        # Extract first 250 words
        words = full_text.split()[:250]
        test_text = ' '.join(words)
        original_word_count = len(words)
        
        logger.info(f"Testing sentence formatting on first 250 words ({original_word_count} words)")
        
        # Process the text
        formatted_text, verified_word_count = identify_sentences(test_text)
        
        # Verify word count remains the same
        if original_word_count != verified_word_count:
            logger.error(f"Word count mismatch! Original: {original_word_count}, Verified: {verified_word_count}")
            return False
        
        # Verify newlines were added
        if '\n' not in formatted_text:
            logger.error("No sentence boundaries found - no newlines added")
            return False
            
        # Verify no content was changed
        formatted_words = formatted_text.replace('\n', ' ').split()
        if formatted_words != words:
            logger.error("Content was modified during formatting")
            return False
            
        logger.info("Sentence formatting test passed successfully!")
        logger.debug(f"Formatted text sample:\n{formatted_text[:500]}...")
        return True
        
    except Exception as e:
        logger.error(f"Sentence formatting test failed: {str(e)}")
        return False

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting sentence formatting tests...")
    test_sentence_formatting()