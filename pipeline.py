import re
import logging
import asyncio
from typing import List, Optional
from alignment import AlignmentProcessor

class TextFormatter:
    """Handles text formatting with proper sentence and paragraph structure."""
    
    def __init__(self):
        self.paragraph_splitter = re.compile(r'\n\s*\n')
        self.sentence_splitter = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s')
        self.logger = logging.getLogger(__name__)
    
    async def format_chunk(self, chunk: str) -> str:
        """Formats a text chunk into proper sentences and paragraphs."""
        paragraphs = []
        for para in self.paragraph_splitter.split(chunk):
            if not para.strip():
                continue
                
            sentences = self.sentence_splitter.split(para)
            formatted_sentences = []
            
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                if sent and sent[-1] not in {'.', '?', '!'}:
                    sent += '.'
                formatted_sentences.append(sent[0].upper() + sent[1:])
            
            paragraphs.append(' '.join(formatted_sentences))
        
        return '\n\n'.join(paragraphs)

class TextProcessingPipeline:
    """Complete text processing pipeline."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.aligner = AlignmentProcessor()
        self.formatter = TextFormatter()
        self.logger = logging.getLogger(__name__)
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap."""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = current_chunk[-self.chunk_overlap:]
                current_length = sum(len(w) + 1 for w in current_chunk)
            current_chunk.append(word)
            current_length += len(word) + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        return chunks
    
    async def process_file(self, input_path: str, output_path: str) -> None:
        """Process input file and write formatted output."""
        try:
            with open(input_path, 'r') as f:
                text = f.read()
            
            chunks = self._chunk_text(text)
            formatted_paragraphs = []
            previous_tail = ""
            
            for chunk in chunks:
                formatted = await self.formatter.format_chunk(previous_tail + ' ' + chunk)
                new_content = self.aligner.extract_new_content(formatted, previous_tail)
                formatted_paragraphs.append(new_content)
                previous_tail = self.aligner.get_tail_for_context(formatted)
            
            with open(output_path, 'w') as f:
                f.write('\n\n'.join(formatted_paragraphs))
                
        except Exception as e:
            self.logger.error(f"Processing failed: {str(e)}")
            raise