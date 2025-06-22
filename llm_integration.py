# llm_integration.py
import aiohttp
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class MyLLMClient:
    """Enhanced LLM client with better error handling."""
    
    def __init__(self, api_url: str = "http://0.0.0.0:5000/v1/completions"):
        self.api_url = api_url
        self.timeout = aiohttp.ClientTimeout(total=120)  # Increased timeout
    
    async def generate(self, prompt: str) -> str:
        """Generate formatted text from prompt with validation."""
        payload = {
            "prompt": prompt,
            "max_tokens": 2000,
            "temperature": 0.7,
            "stop": ["\n\n"],
            "top_p": 0.9,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.5
        }
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                async with session.post(
                    self.api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if response.status != 200:
                        error = await response.text()
                        logger.error(f"LLM API error: {error}")
                        raise ValueError(f"API returned {response.status}")
                        
                    data = await response.json()
                    result = data.get("choices", [{}])[0].get("text", "").strip()
                    
                    if not result:
                        raise ValueError("Empty response from LLM")
                        
                    return result
                    
            except Exception as e:
                logger.error(f"LLM communication failed: {str(e)}")
                raise ValueError(f"LLM error: {str(e)}")