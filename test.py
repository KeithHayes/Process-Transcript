import logging
import aiohttp
import asyncio
from config import API_URL, API_TIMEOUT, MAX_TOKENS, TEMPERATURE, STOP_SEQUENCES, REPETITION_PENALTY, TOP_P

class LLMFormatter:
    def __init__(self, api_url: str = API_URL):
        self.api_url = api_url
        self.logger = logging.getLogger('llm')

    async def format_text(self, text: str) -> str:
        """Format text by adding sentence separation with newlines"""
        self.logger.info(f"Formatting {len(text)} character text")
        
        prompt = f"""Reformat this text with proper sentence separation:

{text}

Rules:
1. Preserve ALL original words exactly
2. Maintain original word order
3. Only add newlines between sentences
4. Do not add any punctuation
5. Replace spaces with newlines around complete sentences
6. Keep final space if present

Example:
Input: 'the cat sat it was happy'
Output: 'the cat sat\nit was happy '

Formatted text:"""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json={
                        "prompt": prompt,
                        "max_tokens": MAX_TOKENS,
                        "temperature": TEMPERATURE,
                        "stop": STOP_SEQUENCES,
                        "repetition_penalty": REPETITION_PENALTY,
                        "top_p": TOP_P
                    },
                    timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
                ) as response:
                    
                    if response.status != 200:
                        error = await response.text()
                        self.logger.error(f"API error: {error}")
                        return text
                    
                    result = await response.json()
                    output = result.get("choices", [{}])[0].get("text", text).strip()
                    
                    # Basic validation
                    if not output.replace('\n', ' ') == text.replace('\n', ' '):
                        self.logger.warning("Output does not match input text")
                        return text
                        
                    return output
                    
        except Exception as e:
            self.logger.error(f"Formatting failed: {str(e)}")
            return text

async def test_formatting():
    """Test the formatter with sample text"""
    formatter = LLMFormatter()
    test_text = "alice warren sat beside a wide window in the corner of her study the late afternoon light slanted gently across the hardwood floor"
    
    formatted = await formatter.format_text(test_text)
    
    print("Original:")
    print(test_text)
    print("\nFormatted:")
    print(formatted)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(test_formatting())