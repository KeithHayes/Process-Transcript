# llm_integration.py
import aiohttp
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class MyLLMClient:
    """Client for interacting with your local LLM API."""
    
    def __init__(self, api_url: str = "http://0.0.0.0:5000/v1/completions"):
        self.api_url = api_url
        self.timeout = aiohttp.ClientTimeout(total=60)
    
    async def generate(self, prompt: str) -> str:
        """
        Send prompt to LLM and return generated text.
        
        Args:
            prompt: Text prompt to send to LLM
            
        Returns:
            Generated text from LLM
        """
        payload = {
            "prompt": prompt,
            "max_tokens": 2000,
            "temperature": 0.7,
            "stop": ["\n\n"]
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
                        raise ValueError(f"LLM API returned {response.status}")
                        
                    data = await response.json()
                    return data.get("choices", [{}])[0].get("text", "").strip()
                    
            except Exception as e:
                logger.error(f"LLM communication failed: {str(e)}")
                raise ValueError(f"LLM communication failed: {str(e)}")