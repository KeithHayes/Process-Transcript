# pipeline.py
import asyncio
import logging
import re
from pathlib import Path
from typing import List, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class TextProcessingPipeline:
    """Complete text processing pipeline with proper chunking, overlap, and formatting."""
    
    def __init__(self, llm, max_retries: int = 3, chunk_size: int = 800, chunk_overlap: int = 200):
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
        self.sentence_end = re.compile(r'(?<=[.!?])\s+')
        self.paragraph_split = re.compile(r'\n\s*\n')
        self.min_paragraph_len = 3  # Minimum sentences per paragraph
        self.context_tail_length = 200  # Length of context to keep between chunks

    async def process_file(self, input_path: str, output_path: str) -> None:
        """Process input file and write formatted output with proper overlap handling."""
        try:
            text = self._read_file(input_path)
            chunks = self._create_chunks(text)
            logger.info(f"Created {len(chunks)} chunks from input")
            
            results = []
            previous_tail = ""  # Stores the overlapping context between chunks
            
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)} (length: {len(chunk)})")
                
                # Combine previous context with current chunk
                combined = previous_tail + chunk
                formatted = await self._format_with_llm(combined)
                
                if not self._validate_formatting(formatted):
                    raise ValueError("LLM returned improperly formatted text")
                
                # Extract only the new content (excluding the overlap)
                new_content = self._extract_new_content(formatted, previous_tail)
                processed = self._post_process(new_content)
                
                results.append(processed)
                # Get the tail of this chunk to use as context for next chunk
                previous_tail = self._get_context_tail(formatted)
            
            # Combine all processed chunks into final output
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
        """Create chunks while respecting sentence boundaries with proper overlap."""
        sentences = self.sentence_end.split(text)
        chunks = []
        current_chunk = []
        current_length = 0
        overlap_buffer = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Ensure proper capitalization
            if sentence and not sentence[0].isupper():
                sentence = sentence[0].upper() + sentence[1:]
                
            # If adding this sentence would exceed chunk size (and we have content)
            if current_length + len(sentence) > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                
                # Prepare overlap for next chunk
                overlap_buffer = []
                overlap_length = 0
                # Add sentences from end until we reach overlap size
                for s in reversed(current_chunk):
                    if overlap_length + len(s) > self.chunk_overlap:
                        break
                    overlap_buffer.insert(0, s)
                    overlap_length += len(s)
                
                # Start next chunk with the overlap
                current_chunk = overlap_buffer
                current_length = overlap_length
            
            current_chunk.append(sentence)
            current_length += len(sentence)
        
        # Add any remaining text as the final chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks

    async def _format_with_llm(self, text: str) -> str:
        """Format text with strict requirements including overlap handling."""
        prompt = f"""Convert this raw transcript into properly formatted text:
        
Requirements:
1. Use complete sentences with proper punctuation
2. Add paragraph breaks every 3-5 sentences
3. Capitalize first letters and proper nouns
4. Remove filler words (uh, um)
5. Maintain original meaning and factual content
6. Use double newlines between paragraphs
7. Fix any grammatical errors
8. Ensure smooth transitions between sections

Raw Input (includes some overlap from previous section):
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
        sentences = self.sentence_end.split(text)
        if not all(s and s[0].isupper() for s in sentences):
            logger.warning("Validation failed: Sentence capitalization")
            return False
            
        # Check paragraph breaks
        paragraphs = self.paragraph_split.split(text)
        if len(paragraphs) < 2 and len(sentences) > self.min_paragraph_len:
            logger.warning("Validation failed: Missing paragraph breaks")
            return False
            
        # Check punctuation
        if not all(s.rstrip()[-1] in {'.', '?', '!'} for s in sentences if s.strip()):
            logger.warning("Validation failed: Sentence punctuation")
            return False
            
        return True

    def _extract_new_content(self, formatted: str, context: str) -> str:
        """Extract only new content from formatted output, excluding overlap."""
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
        paragraphs = self.paragraph_split.split(text)
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
        """Combine processed chunks into final output with smooth transitions."""
        merged = []
        for i, chunk in enumerate(chunks):
            if i > 0:
                # Ensure proper spacing between chunks
                if not merged[-1].endswith('\n\n'):
                    merged.append('\n\n')
            merged.append(chunk)
        
        final_text = ''.join(merged)
        
        # Final validation
        paragraphs = self.paragraph_split.split(final_text)
        if len(paragraphs) < 2:
            logger.warning("Final output contains insufficient paragraphs")
        
        return final_text