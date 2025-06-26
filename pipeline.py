import re
import logging
import asyncio
import aiohttp
import os
from typing import List
from alignment import AlignmentProcessor
from config import (
    CHUNK_SIZE, CHUNK_OVERLAP, API_URL, API_TIMEOUT,
    MAX_TOKENS, STOP_SEQUENCES, REPETITION_PENALTY,
    TEMPERATURE, TOP_P, INPUT_FILE, OUTPUT_FILE
)

class LLMFormatter:
    """LLM formatter focused only on sentence punctuation"""
    
    def __init__(self, api_url: str = API_URL):
        self.api_url = api_url
        self.logger = logging.getLogger(__name__)

    async def punctuate_text(self, text: str) -> str:
        """Get properly punctuated text preserving all original words"""
        prompt = f"""Correct ONLY punctuation and capitalization in this transcript while preserving ALL original content:

{text}

RULES:
1. ONLY add missing punctuation (.!?) and capitalization
2. PRESERVE ALL original words exactly in order
3. Do not change or remove any words
4. Replace connecting dashes with commas or periods
5. Sentences must start with capital and end with .!?
6. Do not add any new words or change word order

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
                        self.logger.warning(f"API returned status {response.status}")
                        return text
                    
                    result = await response.json()
                    return result.get("choices", [{}])[0].get("text", text).strip()
                    
        except Exception as e:
            self.logger.error(f"API call failed: {str(e)}")
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
        """Split text into chunks with overlap along word boundaries"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                overlap_words = current_chunk[-self.chunk_overlap//5:]
                current_chunk = overlap_words
                current_length = sum(len(w) + 1 for w in overlap_words)
            
            current_chunk.append(word)
            current_length += len(word) + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        return chunks

    async def process_file(self) -> None:
        """Process input file and save punctuated output"""
        self.logger.info(f"Starting processing of {INPUT_FILE}")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Clean line breaks but preserve paragraphs
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
        text = re.sub(r' +', ' ', text).strip()
        
        chunks = self._chunk_text(text)
        formatted_parts = []
        previous_tail = ""
        
        for i, chunk in enumerate(chunks, 1):
            self.logger.info(f"Processing chunk {i}/{len(chunks)}")
            
            combined = f"{previous_tail} {chunk}" if previous_tail else chunk
            punctuated = await self.formatter.punctuate_text(combined)
            
            # Extract new content ensuring we don't duplicate
            new_content = self.aligner.extract_new_content(punctuated, previous_tail)
            if new_content:
                formatted_parts.append(new_content)
                previous_tail = self.aligner.get_tail_for_context(
                    punctuated,
                    target_length=self.chunk_overlap
                )
        
        # Combine with paragraph breaks and fix any remaining formatting issues
        final_text = '\n\n'.join(p for p in formatted_parts if p.strip())
        
        # Post-processing to fix any remaining formatting issues
        final_text = re.sub(r'--+', ', ', final_text)  # Replace multiple dashes with commas
        final_text = re.sub(r'\s+([.,!?])', r'\1', final_text)  # Remove spaces before punctuation
        final_text = re.sub(r'([.!?])([A-Z])', r'\1 \2', final_text)  # Ensure space after sentence end
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(final_text)
        
        self.logger.info(f"Successfully saved formatted output to {OUTPUT_FILE}")
        