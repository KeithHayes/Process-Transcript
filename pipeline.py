# pipeline.py
import asyncio
import logging
import re
from typing import List, Optional
from difflib import SequenceMatcher
from pathlib import Path

logger = logging.getLogger(__name__)

class TextProcessingPipeline:
    """Complete text processing pipeline with formatting, chunking, and validation."""
    
    def __init__(self, llm, max_retries: int = 3, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the text processing pipeline.
        
        Args:
            llm: Language model instance with generate() method
            max_retries: Maximum retry attempts for LLM calls
            chunk_size: Target size for text chunks (in characters)
            chunk_overlap: Overlap between chunks (in characters)
        """
        self.llm = llm
        self.max_retries = max_retries
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.sentence_endings = re.compile(r'(?<=[.!?])\s+')
        self.paragraph_splitter = re.compile(r'\n\s*\n')
        self.min_paragraph_length = 3  # sentences
        self.context_tail_length = 200  # characters

    async def process_file(self, input_path: str, output_path: str) -> None:
        """
        Process input file and write formatted output.
        
        Args:
            input_path: Path to input text file
            output_path: Path to save formatted output
        """
        try:
            text = self._read_file(input_path)
            chunks = self._create_chunks(text)
            logger.info(f"Created {len(chunks)} chunks from input")
            
            results = []
            previous_tail = ""
            
            for i, chunk in enumerate(chunks):
                chunk_info = f"Processing chunk {i+1}/{len(chunks)} (length: {len(chunk)})"
                logger.info(chunk_info)
                
                combined = previous_tail + chunk
                formatted = await self._format_with_llm(combined)
                
                if not self._validate_formatting(formatted):
                    raise ValueError("LLM returned improperly formatted text")
                
                new_content = self._extract_new_content(formatted, previous_tail)
                processed = self._post_process(new_content)
                
                results.append(processed)
                previous_tail = self._get_context_tail(formatted)
            
            final_output = self._merge_results(results)
            self._write_output(output_path, final_output)
            logger.info(f"Successfully processed and saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Processing failed: {str(e)}")
            raise

    def _read_file(self, file_path: str) -> str:
        """Read text from file with validation."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")
        return path.read_text(encoding='utf-8')

    def _write_output(self, file_path: str, content: str) -> None:
        """Write content to file with validation."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    def _create_chunks(self, text: str) -> List[str]:
        """Create chunks while respecting sentence boundaries."""
        sentences = self.sentence_endings.split(text)
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Capitalize first letter if needed
            if sentence and not sentence[0].isupper():
                sentence = sentence[0].upper() + sentence[1:]
                
            if current_length + len(sentence) > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                
                # Maintain overlap for context
                overlap = []
                overlap_length = 0
                for s in reversed(current_chunk):
                    if overlap_length + len(s) > self.chunk_overlap:
                        break
                    overlap.insert(0, s)
                    overlap_length += len(s)
                
                current_chunk = overlap
                current_length = overlap_length
            
            current_chunk.append(sentence)
            current_length += len(sentence)
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks

    async def _format_with_llm(self, text: str) -> str:
        """Format text with proper instructions."""
        prompt = f"""Convert this raw transcript into properly formatted text:
        
Requirements:
1. Use complete sentences with proper punctuation
2. Add paragraph breaks every 3-5 sentences
3. Capitalize first letters and proper nouns
4. Remove filler words (uh, um)
5. Maintain original meaning and factual content
6. Use double newlines between paragraphs
7. Fix any grammatical errors

Raw Input:
{text}

Formatted Output:"""
        
        for attempt in range(self.max_retries):
            try:
                response = await self.llm.generate(prompt)
                if not response:
                    raise ValueError("Empty response from LLM")
                return response.strip()
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"LLM formatting failed after {self.max_retries} attempts")
                    raise
                wait = 1 + attempt  # Exponential backoff
                logger.warning(f"Retry {attempt + 1} for LLM call, waiting {wait}s...")
                await asyncio.sleep(wait)
    
    def _validate_formatting(self, text: str) -> bool:
        """Validate proper formatting rules are followed."""
        if not text:
            return False
            
        # Check sentence structure
        sentences = self.sentence_endings.split(text)
        if not all(s and s[0].isupper() for s in sentences):
            logger.warning("Validation failed: Sentence capitalization")
            return False
            
        # Check paragraph breaks
        paragraphs = self.paragraph_splitter.split(text)
        if len(paragraphs) < 2 and len(sentences) > self.min_paragraph_length:
            logger.warning("Validation failed: Missing paragraph breaks")
            return False
            
        # Check punctuation
        if not all(s.rstrip()[-1] in {'.', '?', '!'} for s in sentences if s.strip()):
            logger.warning("Validation failed: Sentence punctuation")
            return False
            
        return True

    def _extract_new_content(self, formatted: str, context: str) -> str:
        """Extract only new content from formatted output."""
        if not context:
            return formatted
            
        # Find where new content begins using fuzzy matching
        matcher = SequenceMatcher(None, context.lower(), formatted.lower())
        match = matcher.find_longest_match(0, len(context), 0, len(formatted))
        
        if match.size < len(context) * 0.7:  # 70% match threshold
            return formatted
            
        return formatted[match.b + match.size:].lstrip()

    def _get_context_tail(self, text: str) -> str:
        """Get the ending portion of text to use as context for next chunk."""
        if len(text) <= self.context_tail_length:
            return text
            
        # Try to find a paragraph break near the target length
        paragraphs = self.paragraph_splitter.split(text)
        tail = []
        current_length = 0
        
        for para in reversed(paragraphs):
            if current_length + len(para) > self.context_tail_length and tail:
                break
            tail.insert(0, para)
            current_length += len(para) + 2  # Account for paragraph breaks
        
        return '\n\n'.join(tail)

    def _post_process(self, text: str) -> str:
        """Final formatting cleanup."""
        # Ensure proper spacing after punctuation
        text = re.sub(r'([.!?])([^\s])', r'\1 \2', text)
        # Remove double spaces
        text = ' '.join(text.split())
        # Ensure paragraph breaks are consistent
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()

    def _merge_results(self, chunks: List[str]) -> str:
        """Combine processed chunks into final output."""
        merged = []
        for i, chunk in enumerate(chunks):
            if i > 0:
                # Ensure proper spacing between chunks
                if not merged[-1].endswith('\n\n'):
                    merged.append('\n\n')
            merged.append(chunk)
        
        final_text = ''.join(merged)
        
        # Final validation
        paragraphs = self.paragraph_splitter.split(final_text)
        if len(paragraphs) < 2:
            logger.warning("Final output contains insufficient paragraphs")
        
        return final_text