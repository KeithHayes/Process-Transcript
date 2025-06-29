import re
import logging
from config import CLEANED_FILE

logger = logging.getLogger('processor_test')

def clean_llm_output(llm_output, original_text):
    """
    Process LLM output to:
    1. Preserve all original words exactly
    2. Keep only the newlines added between sentences
    3. Remove any other formatting changes
    """
    # Split both texts into words
    original_words = original_text.split()
    llm_words = llm_output.split()
    
    # Verify word count matches
    if len(llm_words) != len(original_words):
        logger.error(f"Word count mismatch: original={len(original_words)}, llm={len(llm_words)}")
        return original_text
    
    # Rebuild text with original words but LLM's newlines
    output_lines = []
    current_line = []
    word_index = 0
    
    # Process LLM output line by line
    for line in llm_output.split('\n'):
        line_words = line.split()
        line_length = len(line_words)
        
        # Get corresponding original words
        original_segment = original_words[word_index:word_index+line_length]
        current_line.extend(original_segment)
        word_index += line_length
        
        # If this was a complete sentence (ends with punctuation)
        if line.strip().endswith(('.', '?', '!')):
            output_lines.append(' '.join(current_line))
            current_line = []
    
    # Add any remaining words
    if current_line:
        output_lines.append(' '.join(current_line))
    
    return '\n'.join(output_lines)

def test_post_processor():
    """Test the post-processing cleanup with actual text from transcript"""
    logger.info("Loading test text...")
    with open(CLEANED_FILE, 'r') as f:
        original_text = f.read()
    
    # Take first 250 words for testing
    test_words = original_text.split()[:250]
    original_segment = ' '.join(test_words)
    
    # Simulate LLM output with newlines between sentences
    llm_output = """alice warren sat beside a wide window in the corner of her study
the late afternoon light slanted gently across the hardwood floor illuminating endless rows of books that lined the walls
she loved the hush of quiet contemplation the soft rustle of turning pages and the subtle comfort of stories held within paper and ink
it was in this exact space that she found solace after a long day of meetings presentations and endless email chains
the silence was not merely an absence of noise it was a presence in itself a companion that whispered in comfortable tones and allowed thoughts to drift unencumbered
outside the garden lay in gentle bloom roses of deep crimson and pale pink nodded in the early breeze while lavender and thyme filled the afternoon air with fragrant sweetness
a pair of robins hopped atop the low stone wall pecking at small insects among the wild clover
occasionally a butterfly orange with black veined wings fluttered past the aging glass and alice followed its slow drifting flight for a moment before returning to her book
such ordinary spectacles when observed with attention held a profound beauty
it was a lesson she had learned early and often that the marvels of life are seldom grand or flashy they are small quiet and easily overlooked
her book an anthology of short stories from the early twentieth century lay open on her lap
the paper was slightly yellowed but sturdy the ink crisp each story contained within had been selected for its faithful representation of time place and character
there was a certain charm in the way authors of that era wove descriptive passages around otherwise trivial actions tying shoelaces pouring tea gazing out toward a stormy horizon
such attentiveness to detail formed a tapestry of everyday life and it fascinated alice how these small gestures could reveal so much about an individuals hopes fears and inner world"""
    
    logger.info("Testing post-processing...")
    cleaned = clean_llm_output(llm_output, original_segment)
    
    # Verify the cleaned text matches original words
    if cleaned.replace('\n', ' ') != original_segment:
        logger.error("Post-processing failed to restore original text")
        return False
    
    # Verify newlines were preserved between sentences
    line_count = len(cleaned.split('\n'))
    if line_count < 5:  # Should have multiple lines for this text segment
        logger.error(f"Insufficient newlines - only {line_count} lines found")
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