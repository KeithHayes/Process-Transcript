# pipeline.py
import re
import logging
import asyncio
import aiohttp
from typing import List
from alignment import AlignmentProcessor
from config import (CHUNK_SIZE, CHUNK_OVERLAP, API_URL, API_TIMEOUT,
                   MAX_TOKENS, STOP_SEQUENCES, REPETITION_PENALTY,
                   TEMPERATURE, TOP_P)

class LLMFormatter:
    """Enhanced LLM formatter with robust error handling"""
    
    def __init__(self, api_url: str = API_URL):
        self.api_url = api_url
        self.logger = logging.getLogger(__name__)
        self.call_count = 0

    async def format_with_llm(self, text: str) -> str:
        """Get properly formatted text with fallback processing"""
        self.call_count += 1
        self.logger.info(f"LLM API call #{self.call_count}")
        
        prompt = f"""Reformat this transcript into a professional conversation format:
{text}

Rules:
1. Identify speakers and format as "Name:"
2. Break into logical paragraphs
3. Use proper punctuation (.,!?)
4. Capitalize sentences correctly
5. Remove filler words (uh, um)
6. Maintain original meaning
7. Separate different thoughts/speakers with blank lines

Formatted version:"""

        formatted = await self._try_completion_api(prompt)
        if formatted:
            return self._post_process(formatted)
            
        self.logger.warning("LLM failed, applying basic formatting")
        return self._basic_formatting(text)

    async def _try_completion_api(self, prompt: str) -> str:
        """Attempt to get formatted text from completion API"""
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
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
                ) as response:
                    
                    if response.status != 200:
                        error = await response.text()
                        self.logger.error(f"API Error {response.status}: {error[:200]}")
                        return ""
                    
                    result = await response.json()
                    return result.get("choices", [{}])[0].get("text", "").strip()
                    
        except Exception as e:
            self.logger.error(f"Completion API failed: {str(e)}")
            return ""

    def _basic_formatting(self, text: str) -> str:
        """Apply minimum required formatting"""
        if not text:
            return ""
        
        # Capitalize first letter
        text = text[0].upper() + text[1:] if text else text
        
        # Add period if missing
        if text and text[-1] not in {'.','!','?'}:
            text += '.'
            
        # Basic speaker formatting
        text = re.sub(r'(\w+)\s*(?=:)', r'\1', text)  # "Name :" -> "Name:"
        
        return text

    def _post_process(self, text: str) -> str:
        """Final cleanup"""
        text = re.sub(r'\b(uh|um)\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'(?<=[.,!?])(?=[^\s])', r' ', text)  # Fix spacing
        return text.strip()


class TextProcessingPipeline:
    """Robust processing pipeline with guaranteed output"""
    
    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.aligner = AlignmentProcessor()
        self.formatter = LLMFormatter()
        self.logger = logging.getLogger(__name__)
    
    def _chunk_text(self, text: str) -> List[str]:
        """Precise word-boundary chunking with overlap"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + (1 if current_chunk else 0)  # +1 for space
            
            if current_length + word_length > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                
                # Calculate overlap in words
                overlap_words = []
                overlap_length = 0
                for w in reversed(current_chunk):
                    if overlap_length + len(w) > self.chunk_overlap:
                        break
                    overlap_words.insert(0, w)
                    overlap_length += len(w) + 1
                
                current_chunk = overlap_words
                current_length = overlap_length
            
            current_chunk.append(word)
            current_length += word_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        self.logger.info(f"Created {len(chunks)} chunks (target size: {self.chunk_size}, overlap: {self.chunk_overlap})")
        return chunks

    async def process_file(self, input_path: str, output_path: str) -> None:
        """Process file with guaranteed output"""
        try:
            with open(input_path) as f:
                text = f.read()
            
            # Basic cleaning
            text = re.sub(r'\s+', ' ', text).strip()
            chunks = self._chunk_text(text)
            
            formatted_parts = []
            previous_tail = ""
            
            for i, chunk in enumerate(chunks, 1):
                self.logger.info(f"Processing chunk {i}/{len(chunks)} (size: {len(chunk)} chars)")
                
                combined = f"{previous_tail} {chunk}".strip() if previous_tail else chunk
                self.logger.debug(f"Combined chunk (with overlap): {combined[:200]}...")
                
                formatted = await self.formatter.format_with_llm(combined)
                self.logger.debug(f"LLM response: {formatted[:200]}...")
                
                new_content = self.aligner.extract_new_content(formatted, previous_tail)
                if new_content:
                    formatted_parts.append(new_content)
                    previous_tail = self.aligner.get_tail_for_context(
                        formatted,
                        target_length=self.chunk_overlap
                    )
                else:
                    self.logger.warning(f"Chunk {i} had no new content, using original")
                    formatted_parts.append(chunk)
                    previous_tail = chunk[-self.chunk_overlap:] if len(chunk) > self.chunk_overlap else chunk
            
            final_text = self.aligner.merge_paragraphs(formatted_parts)
            with open(output_path, 'w') as f:
                f.write(final_text or "No content generated")
                
        except Exception as e:
            self.logger.error(f"Processing failed: {str(e)}")
            with open(output_path, 'w') as f:
                f.write("Processing failed. See logs for details.")
            raise