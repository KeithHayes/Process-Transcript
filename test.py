import logging
import aiohttp
import asyncio
import re
from config import CLEANED_FILE, API_URL, API_TIMEOUT, MAX_TOKENS

logger = logging.getLogger('sentence_separator')

class StrictSentenceFormatter:
    def __init__(self, api_url: str = API_URL):
        self.api_url = api_url
        self.logger = logging.getLogger('llm_formatter')

    async def format_sentences(self, text: str) -> str:
        """Format text with newline separation only, with strict validation"""
        self.logger.info(f"Formatting {len(text)} characters")
        
        prompt = f"""ONLY add newlines between sentences in this text. DO NOTHING ELSE:

{text}

RULES:
1. PRESERVE original text EXACTLY
2. ONLY add newlines between sentences
3. DO NOT add punctuation or change capitalization
4. KEEP final space if present

EXAMPLE:
Input: 'the cat sat it was happy'
Output: 'the cat sat\nit was happy '

Formatted text:"""

        try:
            async with aiohttp.ClientSession() as session:
                response = await session.post(
                    self.api_url,
                    json={
                        "prompt": prompt,
                        "max_tokens": MAX_TOKENS,
                        "temperature": 0.1,  # Very low for maximum consistency
                        "stop": ["\n\n"],
                        "repetition_penalty": 2.0,  # Strong penalty for changes
                        "top_p": 0.3,  # Narrow sampling
                        "presence_penalty": 1.5  # Strongly discourage additions
                    },
                    timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
                )
                
                if response.status != 200:
                    error = await response.text()
                    self.logger.error(f"API error: {error}")
                    return text
                    
                result = await response.json()
                output = result.get("choices", [{}])[0].get("text", "").strip()
                
                # Post-process to ensure no modifications
                return self._enforce_rules(text, output)
                
        except Exception as e:
            self.logger.error(f"Formatting failed: {str(e)}")
            return text

    def _enforce_rules(self, original: str, llm_output: str) -> str:
        """Enforce rules by reconstructing output from original words"""
        # Split both texts while preserving spaces
        original_parts = re.split(r'(\s+)', original)
        llm_parts = re.split(r'(\s+)', llm_output)
        
        # Rebuild output using original words but keeping LLM's newlines
        result = []
        for orig, llm in zip(original_parts, llm_parts):
            if orig.isspace() and '\n' in llm:
                result.append('\n')
            else:
                result.append(orig)
        
        formatted = ''.join(result)
        
        # Verify we actually added some newlines
        if '\n' not in formatted:
            self.logger.warning("No newlines added - returning original")
            return original
            
        return formatted

async def test_sentence_separation():
    """Test sentence separation with reconstruction validation"""
    formatter = StrictSentenceFormatter()
    
    # 1. Load test text
    try:
        with open(CLEANED_FILE, 'r') as f:
            text = f.read().strip()
            words = text.split()[:250]
            test_text = ' '.join(words) + ' '  # Ensure trailing space
    except Exception as e:
        logger.error(f"Failed to load input: {str(e)}")
        return False
    
    logger.info(f"Testing with first 250 words ({len(test_text)} chars)")
    
    # 2. Process text
    formatted = await formatter.format_sentences(test_text)
    
    # 3. Validate and show results
    if formatted == test_text:
        logger.error("FAILED: No formatting was applied")
        return False
        
    logger.info("SUCCESS: Formatted output created")
    print("\nFirst 3 sentences:")
    print('\n'.join(formatted.split('\n')[:3]))
    
    # Verify no modifications
    if formatted.replace('\n', ' ') != test_text:
        logger.error("WARNING: Output modifies original text when newlines removed")
        return False
        
    return True

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('sentence_test.log', mode='w'),
            logging.StreamHandler()
        ]
    )
    
    async def main():
        success = await test_sentence_separation()
        exit(0 if success else 1)
    
    asyncio.run(main())