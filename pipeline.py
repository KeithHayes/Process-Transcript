import re
import logging
import asyncio
import aiohttp
import json
from typing import List, Optional
from alignment import AlignmentProcessor

class LLMFormatter:
    def __init__(self, api_url: str = "http://0.0.0.0:5000/v1/completions"):
        self.api_url = api_url
        self.logger = logging.getLogger(__name__)

    async def format_with_llm(self, text: str) -> str:
        """Send text to LLM for formatting into paragraphs/sentences."""
        prompt = f"""
### INSTRUCTIONS:
Rephrase this transcript into **well-structured paragraphs** with **proper grammar**, while **preserving all original content**. Follow these rules:
1. **Fix punctuation, capitalization, and sentence structure**.
2. **Group related ideas into coherent paragraphs**.
3. **Never omit, add, or alter factual content** (names, dates, terms).
4. **Keep speaker labels (e.g., "Pepe Escobar:") intact**.
5. **Remove filler words ("uh", "um") unless they convey meaning**.

### INPUT TRANSCRIPT:
{text}

### FORMATTED OUTPUT:
"""
        payload = {
            "prompt": prompt,
            "max_tokens": 2000,
            "temperature": 0.3,  # Lower = more deterministic
            "stop": ["###", "\n\n\n"],
            "top_p": 0.9,
            "frequency_penalty": 0.1,  # Reduce repetition
            "presence_penalty": 0.1,   # Encourage diversity
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
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
        """Clean up LLM output (e.g., remove extra newlines)."""
        text = re.sub(r"\n{3,}", "\n\n", text)  # Max 2 newlines
        text = re.sub(r"(\w)\.(\w)", r"\1. \2", text)  # Fix missing spaces after periods
        return text.strip()class LLMFormatter:
    def __init__(self, api_url: str = "http://0.0.0.0:5000/v1/completions"):
        self.api_url = api_url
        self.logger = logging.getLogger(__name__)

    async def format_with_llm(self, text: str) -> str:
        """Send text to LLM for formatting into paragraphs/sentences."""
        prompt = f"""
### INSTRUCTIONS:
Rephrase this transcript into **well-structured paragraphs** with **proper grammar**, while **preserving all original content**. Follow these rules:
1. **Fix punctuation, capitalization, and sentence structure**.
2. **Group related ideas into coherent paragraphs**.
3. **Never omit, add, or alter factual content** (names, dates, terms).
4. **Keep speaker labels (e.g., "Pepe Escobar:") intact**.
5. **Remove filler words ("uh", "um") unless they convey meaning**.

### INPUT TRANSCRIPT:
{text}

### FORMATTED OUTPUT:
"""
        payload = {
            "prompt": prompt,
            "max_tokens": 2000,
            "temperature": 0.3,  # Lower = more deterministic
            "stop": ["###", "\n\n\n"],
            "top_p": 0.9,
            "frequency_penalty": 0.1,  # Reduce repetition
            "presence_penalty": 0.1,   # Encourage diversity
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
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
        """Clean up LLM output (e.g., remove extra newlines)."""
        text = re.sub(r"\n{3,}", "\n\n", text)  # Max 2 newlines
        text = re.sub(r"(\w)\.(\w)", r"\1. \2", text)  # Fix missing spaces after periods
        return text.strip()
    
class TextProcessingPipeline:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.chunk_size = chunk_size  # Smaller chunks = better formatting
        self.chunk_overlap = chunk_overlap
        self.aligner = AlignmentProcessor()
        self.formatter = LLMFormatter()

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks, respecting paragraph/sentence boundaries."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current_chunk = []
        current_len = 0

        for para in paragraphs:
            para_len = len(para)
            if current_len + para_len > self.chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                # Keep overlap by retaining last 1-2 paras
                current_chunk = current_chunk[-2:] if len(current_chunk) > 1 else current_chunk[-1:]
                current_len = sum(len(p) for p in current_chunk)
            current_chunk.append(para)
            current_len += para_len

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
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