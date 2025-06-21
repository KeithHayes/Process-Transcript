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
        prompt = f"""Please reformat this transcript into clear paragraphs with proper punctuation:
{text}

Rules:
1. Keep all factual information
2. Fix grammar and capitalization
3. Group related ideas into paragraphs
4. Maintain the original meaning

Formatted version:"""
        
        payload = {
            "prompt": prompt,
            "max_tokens": 2000,
            "temperature": 0.3,
            "stop": ["\n\n"],
            "echo": False,  # Don't echo back the prompt
            "top_p": 0.9,   # Typical sampling parameter
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        error = await response.text()
                        raise ValueError(f"LLM API error {response.status}: {error}")
                    
                    result = await response.json()
                    return result['choices'][0]['text'].strip()
                    
        except Exception as e:
            self.logger.error(f"LLM formatting failed: {str(e)}")
            return text  # Fallback to original text

class TextProcessingPipeline:
    """Complete text processing pipeline with LLM integration"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.aligner = AlignmentProcessor()
        self.formatter = LLMFormatter()
        self.logger = logging.getLogger(__name__)
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks while respecting sentence boundaries"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sent in sentences:
            sent_length = len(sent)
            if current_length + sent_length > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                # Keep overlap for context
                current_chunk = current_chunk[-self.chunk_overlap//20:]
                current_length = sum(len(s) + 1 for s in current_chunk)
            
            current_chunk.append(sent)
            current_length += sent_length + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        return chunks
    
    async def process_file(self, input_path: str, output_path: str) -> None:
        """Process input file through the full pipeline"""
        try:
            with open(input_path, 'r') as f:
                text = f.read()
            
            chunks = self._chunk_text(text)
            formatted_paragraphs = []
            previous_tail = ""
            
            for i, chunk in enumerate(chunks):
                self.logger.info(f"Processing chunk {i+1}/{len(chunks)}")
                
                # Combine with previous context
                combined = f"{previous_tail} {chunk}".strip()
                
                # Format with LLM
                formatted = await self.formatter.format_with_llm(combined)
                if not formatted.strip():
                    self.logger.warning(f"Empty LLM response for chunk {i+1}")
                    formatted = chunk
                
                # Extract new content
                new_content = self.aligner.extract_new_content(formatted, previous_tail)
                formatted_paragraphs.append(new_content)
                
                # Update context for next chunk
                previous_tail = self.aligner.get_tail_for_context(
                    formatted,
                    target_length=self.chunk_overlap
                )
            
            # Merge all paragraphs
            final_text = self.aligner.merge_paragraphs(formatted_paragraphs)
            
            with open(output_path, 'w') as f:
                f.write(final_text)
                
        except Exception as e:
            self.logger.error(f"Processing failed: {str(e)}")
            raise