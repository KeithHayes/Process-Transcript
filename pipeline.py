import re
import logging
import asyncio
import aiohttp
import json
from typing import List, Optional
from alignment import AlignmentProcessor

class LLMFormatter:
    """Handles text formatting using the LLM API"""
    
    def __init__(self, api_url: str = "http://0.0.0.0:5000/v1/completions"):
        self.api_url = api_url
        self.logger = logging.getLogger(__name__)
        self.call_count = 0  # Track API calls
    
    async def format_with_llm(self, text: str) -> str:
        """Send text to LLM for proper formatting"""
        self.call_count += 1
        self.logger.info(f"Making LLM API call #{self.call_count}")
        
        prompt = f"""
### INSTRUCTIONS:
Transform this raw transcript into a well-written essay with:
1. Proper paragraphs separated by blank lines
2. Correct grammar, punctuation and capitalization
3. Meaningful section headings
4. Speaker labels preserved
5. No connecting dashes - use proper transitions

### BAD EXAMPLE:
hi everybody today is saturday welcome back pepe its 11 in moscow i just arrived from st petersburg

### GOOD EXAMPLE:
**Introduction**

Today is Saturday. Welcome back, Pepe.

It's 11 PM in Moscow. I just arrived from St. Petersburg to be here tonight.

### INPUT TRANSCRIPT:
{text}

### PROPERLY FORMATTED OUTPUT:
"""
        
        payload = {
            "prompt": prompt,
            "max_tokens": 2500,
            "temperature": 0.2,
            "stop": ["###", "\n\n\n"],
            "top_p": 0.9,
            "frequency_penalty": 0.2,
            "presence_penalty": 0.2
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=180)
                ) as response:
                    
                    if response.status != 200:
                        error = await response.text()
                        self.logger.error(f"API Error: {error}")
                        return text

                    result = await response.json()
                    formatted = result["choices"][0]["text"].strip()
                    return self._post_process(formatted)
                    
        except Exception as e:
            self.logger.error(f"LLM Error: {str(e)}")
            return text

    def _post_process(self, text: str) -> str:
        """Final cleanup of formatted text"""
        # Ensure proper spacing after punctuation
        text = re.sub(r'(?<=[.,!?])(?=[^\s])', r' ', text)
        # Remove any remaining filler words
        text = re.sub(r'\b(uh|um)\b', '', text, flags=re.IGNORECASE)
        # Ensure consistent paragraph spacing
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


class TextProcessingPipeline:
    """Complete text processing pipeline with LLM integration"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.aligner = AlignmentProcessor()
        self.formatter = LLMFormatter()
        self.logger = logging.getLogger(__name__)
    
    def _chunk_text(self, text: str) -> List[str]:
        """Improved chunking that respects natural breaks"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sent_length = len(sentence)
            
            if current_length + sent_length > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                # Keep overlap for context
                overlap_start = max(0, len(current_chunk) - 3)
                current_chunk = current_chunk[overlap_start:]
                current_length = sum(len(s) for s in current_chunk)
            
            current_chunk.append(sentence)
            current_length += sent_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    async def process_file(self, input_path: str, output_path: str) -> None:
        try:
            with open(input_path, 'r') as f:
                text = f.read()
            
            # Pre-process to clean up raw transcript
            text = re.sub(r'(\w)-(\w)', r'\1 \2', text)  # Remove connecting dashes
            text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
            
            chunks = self._chunk_text(text)
            self.logger.info(f"Created {len(chunks)} chunks from input")
            
            formatted_paragraphs = []
            previous_tail = ""
            
            for i, chunk in enumerate(chunks):
                self.logger.info(f"Processing chunk {i+1}/{len(chunks)} (length: {len(chunk)})")
                
                combined = f"{previous_tail}\n\n{chunk}".strip()
                formatted = await self.formatter.format_with_llm(combined)
                
                if not formatted.strip():
                    self.logger.warning(f"Empty LLM response for chunk {i+1}")
                    formatted = chunk
                
                new_content = self.aligner.extract_new_content(formatted, previous_tail)
                formatted_paragraphs.append(new_content)
                
                previous_tail = self.aligner.get_tail_for_context(
                    formatted,
                    target_length=self.chunk_overlap
                )
            
            final_text = self.aligner.merge_paragraphs(formatted_paragraphs)
            
            with open(output_path, 'w') as f:
                f.write(final_text)
                
        except Exception as e:
            self.logger.error(f"Processing failed: {str(e)}")
            raise