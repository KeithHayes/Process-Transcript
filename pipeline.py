import re
import logging
import asyncio
import aiohttp
from typing import List
from alignment import AlignmentProcessor
from config import (
    CHUNK_SIZE, CHUNK_OVERLAP, API_URL, API_TIMEOUT,
    MAX_TOKENS, STOP_SEQUENCES, REPETITION_PENALTY,
    TEMPERATURE, TOP_P, MIN_SENTENCE_LENGTH
)

class LLMFormatter:
    """Enhanced LLM formatter with strict formatting rules"""
    
    def __init__(self, api_url: str = API_URL):
        self.api_url = api_url
        self.logger = logging.getLogger(__name__)
        self.call_count = 0

    async def format_with_llm(self, text: str) -> str:
        """Get properly formatted text with strict rules"""
        self.call_count += 1
        self.logger.info(f"LLM API call #{self.call_count}")
        
        prompt = f"""Reformat this transcript with STRICT rules:
{text}

RULES:
1. COMPLETE SENTENCES ONLY (must end with .!?)
2. PROPER SPEAKER FORMAT: "Name: content" (if speakers present)
3. CORRECT CAPITALIZATION
4. NO SENTENCE FRAGMENTS
5. PROPER PUNCTUATION (replace dashes with commas or periods)
6. REMOVE FILLER WORDS (uh, um)
7. MAINTAIN ORIGINAL MEANING
8. PRESERVE ALL ORIGINAL CONTENT
9. ENSURE PROPER SPACING AFTER PUNCTUATION
10. FORMAT LISTS AND DIALOGUE PROPERLY

Formatted version must:
- Be grammatically correct
- Maintain original factual content
- Flow naturally
- Preserve all important details

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
        """Final cleanup with enhanced rules"""
        # Remove filler words
        text = re.sub(r'\b(uh|um|ah|er)\b', '', text, flags=re.IGNORECASE)
        
        # Fix spacing and punctuation
        text = re.sub(r'\s+', ' ', text)  # Normalize spaces
        text = re.sub(r'(?<=[.,!?])(?=[^\s])', r' ', text)  # Add missing spaces
        text = re.sub(r'\s([.,!?])', r'\1', text)  # Remove spaces before punctuation
        
        # Fix common punctuation issues
        text = re.sub(r',\s*,', ',', text)  # Remove duplicate commas
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Add space between words
        
        # Ensure proper paragraph breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()

class TextProcessingPipeline:
    """Enhanced processing pipeline with validation"""
    
    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.aligner = AlignmentProcessor()
        self.formatter = LLMFormatter()
        self.logger = logging.getLogger(__name__)
    
    def _chunk_text(self, text: str) -> List[str]:
        """Improved chunking that respects sentence boundaries"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for i, word in enumerate(words):
            word_length = len(word) + 1  # +1 for space
            
            if current_length + word_length > self.chunk_size and current_chunk:
                # Look ahead to find a natural break point
                look_ahead = 0
                while i + look_ahead < len(words) - 1:
                    next_word = words[i + look_ahead]
                    if '.' in next_word or '?' in next_word or '!' in next_word:
                        # Include this punctuation in current chunk
                        for j in range(look_ahead + 1):
                            current_chunk.append(words[i + j])
                            current_length += len(words[i + j]) + 1
                        i += look_ahead
                        break
                    look_ahead += 1
                    
                chunks.append(' '.join(current_chunk))
                
                # Calculate overlap preserving full sentences
                overlap_words = []
                overlap_length = 0
                for w in reversed(current_chunk):
                    if overlap_length + len(w) > self.chunk_overlap * 0.8:  # 80% threshold
                        break
                    overlap_words.insert(0, w)
                    overlap_length += len(w) + 1
                
                current_chunk = overlap_words
                current_length = overlap_length
            
            current_chunk.append(word)
            current_length += word_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        self.logger.info(f"Created {len(chunks)} chunks")
        return chunks

    async def process_file(self, input_path: str, output_path: str) -> None:
        """Process file with enhanced validation and overlap handling"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Initial cleaning - preserve paragraph breaks but normalize other whitespace
            text = re.sub(r'(?<!\n)\s+', ' ', text).strip()
            chunks = self._chunk_text(text)
            
            formatted_parts = []
            previous_tail = ""
            
            for i, chunk in enumerate(chunks, 1):
                self.logger.info(f"Processing chunk {i}/{len(chunks)}")
                
                # Combine with previous tail for context
                combined = f"{previous_tail} {chunk}".strip() if previous_tail else chunk
                formatted = await self.formatter.format_with_llm(combined)
                
                # Validate before adding
                errors = self.aligner.validate_sentences(formatted)
                if errors:
                    self.logger.warning(f"Chunk {i} formatting issues: {errors[:3]}")
                    # Apply additional fixes for validation errors
                    formatted = self.aligner._repair_sentence_boundary(formatted)

                # Extract new content and update tail
                new_content = self.aligner.extract_new_content(formatted, previous_tail)
                if new_content:
                    formatted_parts.append(new_content)
                    previous_tail = self.aligner.get_tail_for_context(
                        formatted,
                        target_length=self.chunk_overlap
                    )
                
            # Combine all parts with paragraph breaks
            final_text = '\n\n'.join(formatted_parts)
            
            # Final cleanup pass
            final_text = re.sub(r'\n{3,}', '\n\n', final_text)
            final_text = re.sub(r'([.!?])([A-Z])', r'\1 \2', final_text)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_text)
                
            self.logger.info(f"Successfully processed {len(chunks)} chunks")
                
        except Exception as e:
            self.logger.error(f"Processing failed: {str(e)}")
            raise