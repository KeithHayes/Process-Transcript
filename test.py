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
                    "stop": ["\n\n"]
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

async def test_llm_processing():
    """Test the actual LLM sentence processing workflow"""
    logger.info("Starting LLM processing test...")
    
    # 1. Read raw unformatted text
    with open(CLEANED_FILE, 'r') as f:
        raw_text = f.read().strip()
    
    # Take first 250 words for testing
    test_words = raw_text.split()[:250]
    test_text = ' '.join(test_words)
    logger.info(f"Test text length: {len(test_text)} chars")

    # 2. Create proper LLM prompt
    prompt = (
        "Please format this unpunctuated text into proper sentences.\n"
        "Rules:\n"
        "1. Add correct punctuation\n"
        "2. Put each sentence on its own line\n"
        "3. Preserve all original words\n"
        "4. Do not add or remove any words\n\n"
        f"Text to format:\n{test_text}\n\n"
        "Formatted text:"
    )

    # 3. Call LLM to process text
    logger.info("Calling LLM to process text...")
    llm_output = await call_llm(prompt)
    if not llm_output:
        logger.error("LLM processing failed")
        return False

    logger.debug(f"LLM output:\n{llm_output}")

    # 4. Verify output
    # a) Check we have newlines between sentences
    if '\n' not in llm_output:
        logger.error("No sentence separation found in LLM output")
        return False

    # b) Verify original words are preserved
    original_words = test_text.split()
    processed_words = llm_output.replace('\n', ' ').split()
    
    if original_words != processed_words:
        logger.error("Word content mismatch between input and output")
        logger.error(f"Original words: {original_words[:10]}...")
        logger.error(f"Processed words: {processed_words[:10]}...")
        return False

    logger.info("LLM processing test passed successfully")
    return True

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def run_test():
        if await test_llm_processing():
            logger.info("SUCCESS: LLM processing works correctly")
        else:
            logger.error("FAILURE: LLM processing issues found")
    
    asyncio.run(run_test())