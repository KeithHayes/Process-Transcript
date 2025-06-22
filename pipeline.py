# pipeline.py
import asyncio
import logging
import time
from typing import List, Optional, Tuple
from difflib import SequenceMatcher
import re

logger = logging.getLogger(__name__)

class TextProcessingPipeline:
    """Enhanced pipeline with better error handling and validation."""

    def __init__(self, llm, max_retries: int = 3, retry_delay: float = 1.0):
        self.llm = llm
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_backoff = 1.5  # Exponential backoff factor

    async def process_file(self, input_path: str, output_path: str) -> None:
        """Process file with enhanced error handling."""
        try:
            for attempt in range(self.max_retries + 1):
                try:
                    await self._process_with_retry(input_path, output_path, attempt)
                    return
                except ValueError as e:
                    if "invalid formatting" in str(e) and attempt < self.max_retries:
                        delay = self.retry_delay * (self.retry_backoff ** attempt)
                        logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.1f}s...")
                        await asyncio.sleep(delay)
                        continue
                    raise
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}")
            raise

    async def _process_with_retry(self, input_path: str, output_path: str, attempt: int) -> None:
        """Process file with validation checks."""
        logger.info(f"Processing attempt {attempt + 1}")
        
        text = self._read_file(input_path)
        chunks = self._create_chunks(text)
        logger.info(f"Created {len(chunks)} chunks from input")
        
        results = []
        previous_tail = ""
        
        for i, chunk in enumerate(chunks):
            chunk_info = f"Processing chunk {i+1}/{len(chunks)} (length: {len(chunk)})"
            logger.info(chunk_info)
            
            combined = previous_tail + chunk
            logger.info(f"Making LLM API call #{i+1}")
            
            formatted = await self._safe_format_with_llm(combined)
            
            # Validate LLM output
            if not self._validate_llm_output(formatted, combined):
                logger.error("LLM returned invalid formatting")
                raise ValueError("LLM returned invalid formatting")
                
            new_content = self._extract_new_content(formatted, previous_tail)
            trimmed = self._trim_last_paragraph(new_content)
            
            results.append(trimmed)
            previous_tail = self._get_context_tail(formatted)
            
        self._write_output(output_path, results)

    async def _safe_format_with_llm(self, text: str) -> str:
        """Format text with LLM including timeout handling."""
        try:
            # Add timeout to prevent hanging
            return await asyncio.wait_for(
                self.llm.format(text),
                timeout=30.0  # 30 second timeout
            )
        except asyncio.TimeoutError:
            logger.error("LLM call timed out")
            raise ValueError("LLM call timed out")

    def _validate_llm_output(self, output: str, input_text: str) -> bool:
        """Validate LLM output meets requirements."""
        if not output:
            return False
            
        # Check if output contains key elements from input
        input_keywords = set(re.findall(r'\w{5,}', input_text[:100]))  # First 100 chars
        output_keywords = set(re.findall(r'\w{5,}', output[:200]))  # First 200 chars
        
        if not input_keywords.intersection(output_keywords):
            return False
            
        # Check for minimum reasonable length
        if len(output) < len(input_text) * 0.5:  # At least 50% of input length
            return False
            
        return True

    def _extract_new_content(self, formatted: str, context: str) -> str:
        """Extract only new content from formatted output."""
        if not context:
            return formatted
            
        # Find where new content begins
        matcher = SequenceMatcher(None, context.lower(), formatted.lower())
        match = matcher.find_longest_match(0, len(context), 0, len(formatted))
        
        if match.size < len(context) * 0.7:  # 70% match threshold
            return formatted
            
        return formatted[match.b + match.size:].lstrip()

    # ... (keep your existing helper methods for file I/O, chunking, etc.)

# Example usage in run.py:
async def main():
    from llm_integration import MyLLMClient  # Your LLM integration
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        llm = MyLLMClient()
        pipeline = TextProcessingPipeline(llm, max_retries=3)
        await pipeline.process_file("input.txt", "output.txt")
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())