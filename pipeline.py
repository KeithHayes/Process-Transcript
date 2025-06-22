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
        self.call_count = 0

    async def format_with_llm(self, text: str) -> str:
        """Send text to LLM for proper formatting"""
        self.call_count += 1
        self.logger.info(f"Making LLM API call #{self.call_count}")
        
        prompt = f"""
### RAW TRANSCRIPT:
{text}

### FORMATTING RULES:
1. Organize into paragraphs with blank lines between
2. Use proper punctuation (.,!?)
3. Capitalize sentences and proper nouns
4. Add section headings where appropriate
5. Format speaker turns like:
   SpeakerName:
   Actual words spoken

### EXAMPLE OUTPUT:
**Introduction**

Participant1:
Welcome everyone. Today we're discussing important matters.

Participant2:
Thank you for having me. I'll begin with the market analysis.

### FORMATTED VERSION:
"""
        
        payload = {
            "prompt": prompt,
            "max_tokens": 1500,
            "temperature": 0.3,
            "stop": ["###"],
            "top_p": 0.8,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    
                    if response.status != 200:
                        error = await response.text()
                        self.logger.error(f"API Error {response.status}: {error[:200]}")
                        raise ValueError(f"API Error {response.status}")

                    result = await response.json()
                    formatted = result["choices"][0]["text"].strip()
                    
                    if not self._validate_output(formatted):
                        self.logger.warning("LLM returned potentially invalid formatting")
                    
                    return self._post_process(formatted)
                    
        except asyncio.TimeoutError:
            self.logger.error("LLM Timeout after 300 seconds")
            raise
        except Exception as e:
            self.logger.error(f"LLM Communication Failed: {str(e)}")
            raise

    def _validate_output(self, text: str) -> bool:
        """Check basic formatting requirements"""
        has_paragraphs = '\n\n' in text
        has_punctuation = any(c in text for c in '.!?')
        has_capitals = any(w[0].isupper() for w in text.split() if w)
        return has_paragraphs and has_punctuation and has_capitals

    def _post_process(self, text: str) -> str:
        """Final cleanup of formatted text"""
        text = re.sub(r'(?<=[.,!?])(?=[^\s])', r' ', text)
        text = re.sub(r'\b(uh|um)\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


class TextProcessingPipeline:
    """Complete text processing pipeline with LLM integration"""
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.aligner = AlignmentProcessor()
        self.formatter = LLMFormatter()
        self.logger = logging.getLogger(__name__)
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks that strictly respect word boundaries"""
        words = text.split(' ')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + (1 if current_chunk else 0)
            
            if current_length + word_length > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)
                
                overlap_words = []
                overlap_length = 0
                for w in reversed(current_chunk):
                    if overlap_length + len(w) + 1 > self.chunk_overlap:
                        break
                    overlap_words.insert(0, w)
                    overlap_length += len(w) + 1
                
                current_chunk = overlap_words
                current_length = overlap_length
            
            current_chunk.append(word)
            current_length += len(word) + (1 if current_chunk else 0)
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        self._validate_chunks(chunks)
        self.logger.debug(f"Created {len(chunks)} chunks with sizes: {[len(c) for c in chunks]}")
        return chunks
    
    def _validate_chunks(self, chunks: List[str]):
        """Ensure chunks meet requirements"""
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i-1]
            curr_chunk = chunks[i]
            
            if not prev_chunk.endswith(' ') and not curr_chunk.startswith(' '):
                last_word = prev_chunk.split()[-1]
                if last_word not in curr_chunk.split()[0]:
                    self.logger.warning(f"Potential discontinuity between chunks {i-1} and {i}")

    async def process_file(self, input_path: str, output_path: str) -> None:
        try:
            with open(input_path, 'r') as f:
                text = f.read()
            
            text = re.sub(r'(\w)-(\w)', r'\1 \2', text)
            text = re.sub(r'\s+', ' ', text).strip()
            
            chunks = self._chunk_text(text)
            self.logger.info(f"Created {len(chunks)} chunks from input")
            
            formatted_paragraphs = []
            previous_tail = ""
            
            for i, chunk in enumerate(chunks):
                self.logger.info(f"Processing chunk {i+1}/{len(chunks)} (length: {len(chunk)})")
                
                combined = f"{previous_tail} {chunk}".strip() if previous_tail else chunk
                formatted = await self.formatter.format_with_llm(combined)
                
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