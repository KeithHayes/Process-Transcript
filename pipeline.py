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
    
    async def format_with_llm(self, text: str) -> str:
        """Send text to LLM for proper formatting"""
        prompt = f"""
### INSTRUCTIONS:
Transform this raw transcript into a well-written essay format with these specific improvements:
1. Break into logical paragraphs with blank lines between them
2. Fix all grammar, punctuation and capitalization
3. Remove filler words (uh, um) unless meaningful
4. Keep all factual content intact
5. Add section headings where appropriate
6. Ensure proper sentence structure throughout
7. Maintain original speaker labels like "Pepe Escobar:"

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
            "max_tokens": 2500,  # Increased for longer outputs
            "temperature": 0.2,   # Lower for more consistent formatting
            "stop": ["###", "\n\n\n"],
            "top_p": 0.9,
            "frequency_penalty": 0.2,
            "presence_penalty": 0.2,
            "best_of": 3          # Get better quality samples
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
                
    def _post_process(self, text: str) -> str:
        """Clean up LLM output with strict formatting rules"""
        # Ensure proper heading formatting
        text = re.sub(r'(?<=\n)([A-Z][a-z]+.*?:)', r'\n**\1**', text)  # Bold speaker labels
        
        # Fix common punctuation issues
        text = re.sub(r'([a-z])\.([A-Z])', r'\1. \2', text)  # Space after periods
        text = re.sub(r'([a-z])\,([A-Z])', r'\1, \2', text)  # Space after commas
        
        # Remove residual filler words
        text = re.sub(r'\b(uh|um)\b[,.]?\s*', '', text, flags=re.IGNORECASE)
        
        # Ensure exactly one blank line between paragraphs
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Capitalize first word after headings
        text = re.sub(r'(^\*\*.*?\*\*)\n([a-z])', 
                     lambda m: f"{m.group(1)}\n{m.group(2).upper()}", 
                     text, flags=re.MULTILINE)
        
        return text.strip()


class TextProcessingPipeline:
    """Complete text processing pipeline with LLM integration"""
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.aligner = AlignmentProcessor()
        self.formatter = LLMFormatter()
        self.logger = logging.getLogger(__name__)
    
    def _chunk_text(self, text: str) -> List[str]:
        """More intelligent chunking that respects paragraphs"""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para)
            
            # Start new chunk if this paragraph would push us over
            if current_length + para_length > self.chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                
                # Carry over last 2 paragraphs for context
                current_chunk = current_chunk[-2:] if len(current_chunk) > 2 else current_chunk.copy()
                current_length = sum(len(p) for p in current_chunk)
            
            current_chunk.append(para)
            current_length += para_length
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    async def process_file(self, input_path: str, output_path: str) -> None:
        try:
            with open(input_path, 'r') as f:
                text = f.read()
            
            chunks = self._chunk_text(text)
            self.logger.info(f"Created {len(chunks)} chunks from input")
            
            formatted_paragraphs = []
            previous_tail = ""
            
            for i, chunk in enumerate(chunks):
                self.logger.info(f"Processing chunk {i+1}/{len(chunks)} (length: {len(chunk)})")
                
                combined = f"{previous_tail}\n\n{chunk}".strip()
                self.logger.debug(f"Combined text sent to LLM:\n{combined[:200]}...")
                
                formatted = await self.formatter.format_with_llm(combined)
                self.logger.debug(f"Formatted response:\n{formatted[:200]}...")
                
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