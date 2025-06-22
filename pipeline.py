# pipeline.py
import re
import logging
import asyncio
import aiohttp
from typing import List
from alignment import AlignmentProcessor

class LLMFormatter:
    """Optimized formatter for Phi-3-mini's behavior"""
    
    def __init__(self, api_url: str = "http://0.0.0.0:5000/v1/completions"):
        self.api_url = api_url
        self.logger = logging.getLogger(__name__)
        self.call_count = 0

    async def format_with_llm(self, text: str) -> str:
        """Get formatted text from Phi-3-mini with proper prompting"""
        self.call_count += 1
        self.logger.info(f"LLM API call #{self.call_count}")
        
        # Phi-3-mini specific prompt structure
        prompt = f"""<|user|>
Please reformat this transcript with:
1. Proper punctuation
2. Paragraph breaks
3. Correct capitalization
4. Speaker formatting like "Name:"
5. No filler words (uh, um)

Transcript:
{text}

Formatted version:<|assistant|>"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json={
                        "prompt": prompt,
                        "max_tokens": 2000,
                        "temperature": 0.3,
                        "stop": ["<|end|>"]
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status != 200:
                        error = await response.text()
                        raise ValueError(f"API Error {response.status}")
                    
                    result = await response.json()
                    formatted = result.get("choices", [{}])[0].get("text", "").strip()
                    
                    if not formatted:
                        raise ValueError("Empty LLM response")
                        
                    return self._post_process(formatted)
                    
        except Exception as e:
            self.logger.error(f"LLM Error: {str(e)}")
            raise

    def _post_process(self, text: str) -> str:
        """Final cleanup"""
        text = re.sub(r'\b(uh|um)\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


class TextProcessingPipeline:
    """Reliable pipeline for Phi-3-mini"""
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.aligner = AlignmentProcessor()
        self.formatter = LLMFormatter()
        self.logger = logging.getLogger(__name__)
    
    def _chunk_text(self, text: str) -> List[str]:
        """Precise word-boundary chunking"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                # Maintain overlap
                overlap_words = int(self.chunk_overlap / 10)  # ~10 chars/word
                current_chunk = current_chunk[-overlap_words:]
                current_length = sum(len(w) for w in current_chunk) + len(current_chunk)
            
            current_chunk.append(word)
            current_length += len(word) + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        self.logger.info(f"Created {len(chunks)} chunks")
        return chunks

    async def process_file(self, input_path: str, output_path: str) -> None:
        """Process file with guaranteed output"""
        try:
            with open(input_path) as f:
                text = f.read()
            
            text = re.sub(r'\s+', ' ', text).strip()
            chunks = self._chunk_text(text)
            
            formatted_parts = []
            previous_tail = ""
            
            for i, chunk in enumerate(chunks, 1):
                self.logger.info(f"Processing chunk {i}/{len(chunks)}")
                
                combined = f"{previous_tail} {chunk}" if previous_tail else chunk
                formatted = await self.formatter.format_with_llm(combined)
                
                new_content = self.aligner.extract_new_content(formatted, previous_tail)
                formatted_parts.append(new_content)
                previous_tail = self.aligner.get_tail_for_context(
                    formatted,
                    target_length=self.chunk_overlap
                )
            
            final_text = self.aligner.merge_paragraphs(formatted_parts)
            with open(output_path, 'w') as f:
                f.write(final_text)
                
        except Exception as e:
            self.logger.error(f"Processing failed: {str(e)}")
            raise