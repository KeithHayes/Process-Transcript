# text_processing_pipeline.py
import asyncio
import logging
from typing import List, Optional, Dict, Any
from difflib import SequenceMatcher
import re
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.text_splitter import TextSplitter

class LineAwareTextSplitter(TextSplitter):
    """Text splitter that maintains line integrity while creating chunks with overlap."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separator: str = "\n",
        keep_separator: bool = True,
    ):
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            keep_separator=keep_separator,
        )
        self._separator = separator
        
    def split_text(self, text: str) -> List[str]:
        """Split text into chunks while respecting line boundaries."""
        lines = text.split(self._separator)
        if self._keep_separator:
            lines = [line + self._separator for line in lines[:-1]] + [lines[-1]]
        
        chunks = []
        current_chunk = []
        current_length = 0
        overlap_buffer = []
        
        for i, line in enumerate(lines):
            line_length = self._length_function(line)
            
            if current_length + line_length > self._chunk_size and current_chunk:
                chunks.append(self._separator.join(current_chunk))
                
                # Prepare overlap for next chunk
                overlap_length = 0
                overlap_buffer = []
                for line in reversed(current_chunk):
                    line_len = self._length_function(line)
                    if overlap_length + line_len <= self._chunk_overlap:
                        overlap_buffer.insert(0, line)
                        overlap_length += line_len
                    else:
                        break
                
                current_chunk = overlap_buffer
                current_length = overlap_length
            
            current_chunk.append(line)
            current_length += line_length
        
        if current_chunk:
            chunks.append(self._separator.join(current_chunk))
        
        return chunks

class AlignmentProcessor:
    """Handles alignment between original and formatted text."""
    
    def __init__(self, min_match_ratio: float = 0.7, min_context_length: int = 50):
        self.paragraph_splitter = re.compile(r'\n\s*\n')
        self.min_match_ratio = min_match_ratio
        self.min_context_length = min_context_length
    
    def extract_new_content(self, combined: str, context: str) -> str:
        """Extract only the new content from LLM output."""
        if not context or len(context) < self.min_context_length:
            return combined
        
        clean_context = ' '.join(context.split())
        clean_combined = ' '.join(combined.split())
        
        matcher = SequenceMatcher(None, clean_context.lower(), clean_combined.lower())
        match = matcher.find_longest_match(0, len(clean_context), 0, len(clean_combined))
        
        if match.size < len(clean_context) * self.min_match_ratio:
            return combined
            
        original_pos = len(combined) - len(clean_combined) + match.b + match.size
        return combined[original_pos:].lstrip()
    
    def drop_last_paragraph(self, text: str, min_paragraph_length: int = 20) -> str:
        """Remove the last paragraph from the text if it exists."""
        paragraphs = [p for p in self.paragraph_splitter.split(text) if p.strip()]
        
        if len(paragraphs) <= 1:
            return text
            
        if len(paragraphs[-1]) < min_paragraph_length:
            return text
            
        return '\n\n'.join(paragraphs[:-1])
    
    def get_tail_for_context(self, text: str, target_length: int = 200) -> str:
        """Get the ending portion of text to use as context for next chunk."""
        if len(text) <= target_length:
            return text
            
        paragraphs = [p for p in self.paragraph_splitter.split(text) if p.strip()]
        
        if len(paragraphs) == 1:
            return text[-target_length:]
            
        accumulated = []
        current_length = 0
        
        for para in reversed(paragraphs):
            if current_length + len(para) > target_length and accumulated:
                break
            accumulated.insert(0, para)
            current_length += len(para) + 2
            
        return '\n\n'.join(accumulated)

class ContextAwareFormatter:
    """Handles the formatting process with context from previous chunks."""
    
    def __init__(self, llm, verbose: bool = False, max_retries: int = 3):
        self.llm = llm
        self.verbose = verbose
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        
        self.format_prompt = PromptTemplate(
            input_variables=["context", "new_content"],
            template="""Format this new content to flow from the given context:
            
Previous Context:
{context}

New Content:
{new_content}

Rules:
1. Maintain all factual information
2. Ensure seamless transition
3. Match the existing style
4. Output ONLY the new formatted content

Formatted Output:"""
        )
        
        self.format_chain = LLMChain(
            llm=self.llm,
            prompt=self.format_prompt,
            verbose=self.verbose
        )
    
    async def format_with_context(self, context: str, new_content: str) -> str:
        """Format new content with awareness of previous context."""
        formatted = await self.format_chain.arun({
            "context": context,
            "new_content": new_content
        })
        return formatted.strip()

class TextProcessingPipeline:
    """Orchestrates the entire text processing workflow."""
    
    def __init__(self, llm, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.splitter = LineAwareTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator="\n"
        )
        self.formatter = ContextAwareFormatter(llm)
        self.aligner = AlignmentProcessor()
        self.progress_callback = None
    
    def set_progress_callback(self, callback):
        """Set a callback for progress updates."""
        self.progress_callback = callback
    
    async def process_file(self, input_path: str, output_path: str) -> None:
        """Process an input file and save results to output file."""
        with open(input_path, 'r') as f:
            text = f.read()
        
        chunks = self.splitter.split_text(text)
        total_chunks = len(chunks)
        final_output = []
        previous_tail = ""
        
        for i, chunk in enumerate(chunks):
            # Format with context
            formatted = await self.formatter.format_with_context(
                context=previous_tail,
                new_content=chunk
            )
            
            # Process the formatted output
            new_content = self.aligner.extract_new_content(formatted, previous_tail)
            trimmed_content = self.aligner.drop_last_paragraph(new_content)
            
            # Update progress
            if self.progress_callback:
                self.progress_callback(i+1, total_chunks)
            
            # Prepare for next iteration
            final_output.append(trimmed_content)
            previous_tail = self.aligner.get_tail_for_context(
                formatted,
                length=self.splitter._chunk_overlap
            )
        
        # Write final output
        with open(output_path, 'w') as f:
            f.write('\n'.join(final_output))

async def main():
    """Example usage with Ollama LLM."""
    from langchain.llms import Ollama
    
    # Initialize LLM
    llm = Ollama(model="mistral")
    
    # Create pipeline
    pipeline = TextProcessingPipeline(
        llm=llm,
        chunk_size=800,
        chunk_overlap=150
    )
    
    # Set up progress tracking
    def progress_callback(current, total):
        print(f"Processing chunk {current}/{total}")
    
    pipeline.set_progress_callback(progress_callback)
    
    # Process file
    await pipeline.process_file(
        input_path="input.txt",
        output_path="output.txt"
    )
    print("Processing complete!")

if __name__ == "__main__":
    asyncio.run(main())

    