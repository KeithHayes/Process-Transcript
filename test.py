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

async def test_sentence_separation():
    """Test sentence separation and punctuation with newlines"""
    logger.info("Starting sentence separation test...")
    
    # 1. Read preprocessed text
    with open(CLEANED_FILE, 'r') as f:
        raw_text = f.read().strip()
    
    # Take first 250 words for testing
    test_words = raw_text.split()[:250]
    test_text = ' '.join(test_words)
    logger.info(f"Test text length: {len(test_text)} chars")

    # 2. Create focused LLM prompt for sentence separation only
    prompt = (
        "Identify and punctuate complete sentences in this text. Follow these rules exactly:\n"
        "1. Preserve all original words exactly\n"
        "2. Maintain original word order\n"
        "3. Do not add any new content\n"
        "4. Only add punctuation where sentences clearly end\n"
        "5. Replace the space before each sentence with a newline\n"
        "6. Replace the space after each sentence with a newline\n"
        "7. Keep the space after the last word if present\n\n"
        "Example:\n"
        "Input: 'she walked the dog it was happy'\n"
        "Output: 'she walked the dog\nit was happy '\n\n"
        f"Text to process:\n{test_text}\n\n"
        "Formatted text:"
    )

    # 3. Call LLM to process text
    logger.info("Calling LLM to identify sentences...")
    llm_output = await call_llm(prompt)
    if not llm_output:
        logger.error("LLM processing failed")
        return False

    logger.debug(f"LLM output:\n{llm_output}")

    # 4. Verify output meets requirements
    # a) Check we have newlines between sentences
    if '\n' not in llm_output:
        logger.error("No sentence separation found in LLM output")
        return False

    # b) Verify original words are preserved in order
    original_words = test_text.split()
    processed_words = llm_output.replace('\n', ' ').split()
    
    if original_words != processed_words:
        logger.error("Word content mismatch between input and output")
        logger.error(f"Original words: {original_words[:10]}...")
        logger.error(f"Processed words: {processed_words[:10]}...")
        return False

    # c) Check length matches (except for space->newline conversions)
    original_length = len(test_text)
    processed_length = len(llm_output.replace('\n', ' '))
    if original_length != processed_length:
        logger.error(f"Length mismatch: original={original_length}, processed={processed_length}")
        return False

    logger.info("Sentence separation test passed successfully")
    return True

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def run_test():
        if await test_sentence_separation():
            logger.info("SUCCESS: Sentence separation works correctly")
        else:
            logger.error("FAILURE: Sentence separation issues found")
    
    asyncio.run(run_test())