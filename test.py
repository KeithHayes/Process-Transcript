import re
import logging
import aiohttp
import asyncio
from config import CLEANED_FILE, API_URL, API_TIMEOUT, MAX_TOKENS

logger = logging.getLogger('processor_test')

async def call_llm(prompt):
    """Make actual LLM API call to process text with detailed error handling"""
    try:
        logger.debug("Creating ClientSession for LLM call")
        async with aiohttp.ClientSession() as session:
            logger.debug(f"Sending request to {API_URL}")
            json_data = {
                "prompt": prompt,
                "max_tokens": MAX_TOKENS,
                "temperature": 0.7,
                "stop": ["\n\n"],
                "repetition_penalty": 1.2,
                "top_p": 0.9
            }
            logger.debug(f"Request payload: {json_data}")
            
            try:
                async with session.post(
                    API_URL,
                    json=json_data,
                    timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
                ) as response:
                    if response.status != 200:
                        error = await response.text()
                        logger.error(f"LLM API error {response.status}: {error}")
                        return None
                    
                    result = await response.json()
                    logger.debug(f"Raw LLM response: {result}")
                    
                    if not result.get("choices"):
                        logger.error("No choices in LLM response")
                        return None
                    
                    output = result["choices"][0].get("text", "").strip()
                    if not output:
                        logger.error("Empty output from LLM")
                        return None
                    
                    logger.debug(f"LLM returned {len(output)} characters")
                    return output
                    
            except asyncio.TimeoutError:
                logger.error("LLM API request timed out")
                return None
            except aiohttp.ClientError as e:
                logger.error(f"HTTP client error: {str(e)}")
                return None
                
    except Exception as e:
        logger.error(f"Unexpected error in LLM call: {str(e)}", exc_info=True)
        return None

async def test_sentence_separation():
    """Test sentence separation with detailed validation"""
    logger.info("Starting sentence separation test with detailed validation")
    
    try:
        # 1. Read and validate input
        with open(CLEANED_FILE, 'r') as f:
            raw_text = f.read().strip()
            if not raw_text:
                logger.error("Input file is empty")
                return False
    except Exception as e:
        logger.error(f"Failed to read input file: {str(e)}", exc_info=True)
        return False
    
    # Take first 250 words for testing
    test_words = raw_text.split()[:250]
    test_text = ' '.join(test_words)
    logger.info(f"Test text length: {len(test_text)} chars")
    logger.debug(f"First 100 chars: {test_text[:100]}...")

    # 2. Create strict prompt with clear examples
    prompt = (
        "REFORMAT THIS TEXT WITH NEWLINES BETWEEN SENTENCES ONLY. RULES:\n"
        "1. PRESERVE ALL ORIGINAL WORDS EXACTLY\n"
        "2. MAINTAIN EXACT WORD ORDER\n"
        "3. NO NEW CONTENT\n"
        "4. ONLY ADD PERIODS AND NEWLINES\n"
        "5. REPLACE SPACE BEFORE/AFTER SENTENCES WITH NEWLINES\n"
        "6. KEEP FINAL SPACE IF PRESENT\n\n"
        "EXAMPLE INPUT: 'the cat sat it was happy'\n"
        "EXAMPLE OUTPUT: 'the cat sat\nit was happy '\n\n"
        "INPUT TEXT TO REFORMAT:\n"
        f"{test_text}\n\n"
        "REFORMATTED OUTPUT:"
    )

    logger.debug("Prompt being sent to LLM:")
    logger.debug(prompt[:500] + ("..." if len(prompt) > 500 else ""))

    # 3. Call LLM with timeout handling
    try:
        logger.info("Calling LLM with timeout of {API_TIMEOUT} seconds")
        llm_output = await asyncio.wait_for(call_llm(prompt), timeout=API_TIMEOUT)
    except asyncio.TimeoutError:
        logger.error("LLM call timed out")
        return False
        
    if not llm_output:
        logger.error("No output received from LLM")
        return False

    logger.info(f"Received {len(llm_output)} chars from LLM")
    logger.debug("LLM output sample:")
    logger.debug(llm_output[:200] + ("..." if len(llm_output) > 200 else ""))

    # 4. Strict validation
    validation_passed = True
    
    # Check for basic requirements
    if '\n' not in llm_output:
        logger.error("FAIL: No newlines found in output")
        validation_passed = False
    
    # Verify word preservation
    original_words = test_text.split()
    processed_words = llm_output.replace('\n', ' ').split()
    
    if len(original_words) != len(processed_words):
        logger.error(f"FAIL: Word count mismatch (orig:{len(original_words)} vs proc:{len(processed_words)})")
        validation_passed = False
    
    for i, (orig, proc) in enumerate(zip(original_words, processed_words)):
        if orig != proc:
            logger.error(f"FAIL: Word changed at position {i}: '{orig}' -> '{proc}'")
            validation_passed = False
            break
    
    # Check length consistency
    orig_len = len(test_text)
    proc_len = len(llm_output.replace('\n', ' '))
    if orig_len != proc_len:
        logger.error(f"FAIL: Length mismatch (orig:{orig_len} vs proc:{proc_len})")
        validation_passed = False
    
    # Check newline formatting
    lines = llm_output.split('\n')
    for i, line in enumerate(lines):
        if i > 0 and not line.strip():
            logger.error(f"FAIL: Empty line at position {i}")
            validation_passed = False
        if line.startswith(' '):
            logger.error(f"FAIL: Line starts with space: '{line[:20]}...'")
            validation_passed = False
        if line.endswith(' ') and i != len(lines)-1:
            logger.error(f"FAIL: Line ends with space: '{line[-20:]}'")
            validation_passed = False

    if validation_passed:
        logger.info("SUCCESS: All validation checks passed")
        return True
    else:
        logger.error("FAILURE: Validation checks failed")
        return False

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('test_debug.log', mode='w'),
            logging.StreamHandler()
        ]
    )
    
    async def main():
        try:
            success = await test_sentence_separation()
            if not success:
                logger.error("TEST FAILED")
                exit(1)
            logger.info("TEST PASSED")
        except Exception as e:
            logger.error(f"Test crashed: {str(e)}", exc_info=True)
            exit(1)
    
    asyncio.run(main())