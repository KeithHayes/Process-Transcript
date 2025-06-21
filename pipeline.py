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
        prompt = f"""Rephrase this transcript into well-structured paragraphs with proper grammar:
        
{text}

Guidelines:
- Keep all factual content
- Fix punctuation and capitalization
- Group related ideas together
- Output in clean paragraphs
- Never omit or add information

Formatted version:\n\n"""
        
        payload = {
            "prompt": prompt,
            "max_tokens": 2000,
            "temperature": 0.5,
            "stop": ["\n\n\n"],
            "top_p": 0.9,
            "frequency_penalty": 0.2,
            "presence_penalty": 0.2,
            "echo": False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    response_text = await response.text()
                    self.logger.debug(f"Raw API response: {response_text}")
                    
                    if response.status != 200:
                        raise ValueError(f"API error {response.status}: {response_text}")
                    
                    result = await response.json()
                    
                    if not result.get('choices'):
                        self.logger.error("No 'choices' in response")
                        return text
                    
                    if not result['choices'][0].get('text'):
                        self.logger.error("No 'text' in choices")
                        return text
                    
                    formatted = result['choices'][0]['text'].strip()
                    if not formatted:
                        self.logger.warning("Empty formatted text received")
                        return text
                    
                    return formatted
                
        except Exception as e:
            self.logger.error(f"LLM formatting failed: {str(e)}")
            return text

class TextProcessingPipeline:
    """Complete text processing pipeline with LLM integration"""
    
    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.aligner = AlignmentProcessor()
        self.formatter = LLMFormatter()
        self.logger = logging.getLogger(__name__)
    
    def _chunk_text(self, text: str) -> List[str]:
        """More conservative chunking approach"""
        paras = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paras:
            para_length = len(para)
            if current_length + para_length > self.chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = current_chunk[-min(2, len(current_chunk)):]
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