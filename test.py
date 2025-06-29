import re
import logging
import aiohttp
import asyncio
from config import CLEANED_FILE, API_URL, API_TIMEOUT, MAX_TOKENS

logger = logging.getLogger('processor_test')

async def call_llm(prompt):
    """Make actual LLM API call to process text"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                API_URL,
                json={
                    "prompt": prompt,
                    "max_tokens": MAX_TOKENS,
                    "temperature": 0.7,
                    "stop": ["\n\n"],
                    "repetition_penalty": 1.2,
                    "top_p": 0.9
                },
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"LLM API error: {error}")
                    return None
                result = await response.json()
                return result.get("choices", [{}])[0].get("text", "").strip()
    except Exception as e:
        logger.error(f"LLM call failed: {str(e)}")
        return None

def log_text_comparison(original, processed, context_lines=3):
    """Log detailed comparison of original vs processed text"""
    logger.debug("=== ORIGINAL TEXT ===")
    logger.debug(original)
    logger.debug("=== PROCESSED TEXT ===")
    logger.debug(processed)
    
    # Find first difference if any
    for i, (orig_char, proc_char) in enumerate(zip(original, processed)):
        if orig_char != proc_char:
            start = max(0, i - 20)
            end = min(len(original), i + 20)
            logger.error(f"First difference at position {i}:")
            logger.error(f"Original: ...{original[start:i]}>>>{original[i]}<<<{original[i+1:end]}...")
            logger.error(f"Processed: ...{processed[start:i]}>>>{processed[i]}<<<{processed[i+1:end]}...")
            break

async def test_sentence_separation():
    """Test sentence separation and punctuation with newlines"""
    logger.info("Starting sentence separation test...")
    
    # 1. Read preprocessed text
    try:
        with open(CLEANED_FILE, 'r') as f:
            raw_text = f.read().strip()
    except Exception as e:
        logger.error(f"Failed to read input file: {str(e)}")
        return False
    
    # Take first 250 words for testing
    test_words = raw_text.split()[:250]
    test_text = ' '.join(test_words)
    logger.info(f"Test text length: {len(test_text)} chars")
    logger.debug(f"Sample of test text: {test_text[:100]}...")

    # 2. Create focused LLM prompt for sentence separation only
    prompt = (
        "IDENTIFY AND FORMAT SENTENCES IN THIS TEXT. FOLLOW THESE RULES EXACTLY:\n"
        "1. Preserve ALL original words exactly as they appear\n"
        "2. Maintain the EXACT original word order\n"
        "3. DO NOT add any new words or content\n"
        "4. Only add punctuation where sentences clearly end\n"
        "5. Replace the space BEFORE each sentence with a newline\n"
        "6. Replace the space AFTER each sentence with a newline\n"
        "7. Keep the space after the last word if present\n"
        "8. DO NOT modify any words - only add punctuation and newlines\n\n"
        "EXAMPLE INPUT: 'she walked the dog it was happy'\n"
        "EXAMPLE OUTPUT: 'she walked the dog\nit was happy '\n\n"
        "TEXT TO PROCESS:\n"
        f"{test_text}\n\n"
        "FORMATTED TEXT:"
    )

    logger.debug("Sending this prompt to LLM:")
    logger.debug(prompt[:500] + "..." if len(prompt) > 500 else prompt)

    # 3. Call LLM to process text
    logger.info("Calling LLM to identify sentences...")
    llm_output = await call_llm(prompt)
    if not llm_output:
        logger.error("LLM processing failed - no output received")
        return False

    logger.debug(f"Raw LLM output:\n{llm_output}")

    # 4. Verify output meets requirements
    test_failed = False
    
    # a) Check we have newlines between sentences
    newline_count = llm_output.count('\n')
    if newline_count == 0:
        logger.error("FAIL: No sentence separation found in LLM output")
        logger.error("Expected newlines between sentences but found none")
        test_failed = True
    else:
        logger.info(f"Found {newline_count} newlines in output")

    # b) Verify original words are preserved in order
    original_words = test_text.split()
    processed_words = llm_output.replace('\n', ' ').split()
    
    if len(original_words) != len(processed_words):
        logger.error(f"FAIL: Word count mismatch - original:{len(original_words)} processed:{len(processed_words)}")
        test_failed = True
    
    for i, (orig, proc) in enumerate(zip(original_words, processed_words)):
        if orig != proc:
            logger.error(f"FAIL: Word mismatch at position {i}:")
            logger.error(f"Original: '{orig}'")
            logger.error(f"Processed: '{proc}'")
            test_failed = True
            break
    
    # c) Check length matches (except for space->newline conversions)
    original_length = len(test_text)
    processed_length = len(llm_output.replace('\n', ' '))
    if original_length != processed_length:
        logger.error(f"FAIL: Length mismatch - original:{original_length} processed:{processed_length}")
        log_text_comparison(test_text, llm_output.replace('\n', ' '))
        test_failed = True

    # d) Check newline placement
    lines = llm_output.split('\n')
    for i, line in enumerate(lines):
        if i > 0 and not line:  # Empty line after newline
            logger.error(f"FAIL: Found empty line at position {i}")
            test_failed = True
        if line.startswith(' '):
            logger.error(f"FAIL: Line starts with space: '{line[:20]}...'")
            test_failed = True
        if line.endswith(' ') and i != len(lines)-1:  # Last line can end with space
            logger.error(f"FAIL: Line ends with space: '{line[-20:]}'")
            test_failed = True

    if test_failed:
        logger.error("FAILURE: Sentence separation issues found")
        return False
    else:
        logger.info("SUCCESS: Sentence separation test passed")
        logger.debug("Final formatted output sample:")
        logger.debug(llm_output[:200] + "..." if len(llm_output) > 200 else llm_output)
        return True

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,  # More verbose logging for debugging
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('test_debug.log'),
            logging.StreamHandler()
        ]
    )
    
    async def run_test():
        try:
            success = await test_sentence_separation()
            if not success:
                logger.error("FAILURE: Sentence separation test failed")
                exit(1)
        except Exception as e:
            logger.error(f"Test crashed: {str(e)}", exc_info=True)
            exit(1)
    
    asyncio.run(run_test())