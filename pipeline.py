import re
import logging
import asyncio
import aiohttp
from typing import List
from alignment import AlignmentProcessor
from config import (
    CHUNK_SIZE, CHUNK_OVERLAP, API_URL, API_TIMEOUT,
    MAX_TOKENS, STOP_SEQUENCES, REPETITION_PENALTY,
    TEMPERATURE, TOP_P
)

class LLMFormatter:
    """LLM formatter focused only on sentence punctuation"""
    
    def __init__(self, api_url: str = API_URL):
        self.api_url = api_url
        self.logger = logging.getLogger(__name__)
        self.call_count = 0

    async def punctuate_text(self, text: str) -> str:
        """Get properly punctuated text preserving all original words"""
        self.call_count += 1
        prompt = f"""Correct punctuation and capitalization in this transcript while preserving ALL original content:

{text}

RULES:
1. ONLY add missing punctuation and capitalization
2. PRESERVE ALL original words exactly
3. Sentences must start with capital and end with .!?
4. Replace connecting dashes with commas or periods
5. Do not change word order or remove any words

Corrected version:"""

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
                        return self._basic_punctuation(text)
                    
                    result = await response.json()
                    return result.get("choices", [{}])[0].get("text", "").strip()
                    
        except Exception:
            return self._basic_punctuation(text)

    def _basic_punctuation(self, text: str) -> str:
        """Apply minimum required punctuation"""
        if not text:
            return ""
        text = text[0].upper() + text[1:] if text else text
        if text and text[-1] not in {'.','!','?'}:
            text += '.'
        return text

class TextProcessingPipeline:
    """Processing pipeline focused on sentence punctuation"""
    
    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.aligner = AlignmentProcessor()
        self.formatter = LLMFormatter()
        self.logger = logging.getLogger(__name__)
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
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
            current_length += len(word) + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        return chunks

    async def process_file(self, input_path: str, output_path: str) -> None:
        """Process input file and save punctuated output"""
        with open(input_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
        text = re.sub(r' +', ' ', text).strip()
        
        chunks = self._chunk_text(text)
        formatted_parts = []
        previous_tail = ""
        
        for chunk in chunks:
            combined = f"{previous_tail} {chunk}" if previous_tail else chunk
            punctuated = await self.formatter.punctuate_text(combined)
            new_content = self.aligner.extract_new_content(punctuated, previous_tail)
            if new_content:
                formatted_parts.append(new_content)
                previous_tail = self.aligner.get_tail_for_context(
                    punctuated,
                    target_length=self.chunk_overlap
                )
        
        final_text = '\n\n'.join(p for p in formatted_parts if p.strip())
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_text)