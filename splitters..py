from typing import List, Optional
from langchain.text_splitter import TextSplitter

class LineAwareTextSplitter(TextSplitter):
    """
    Text splitter that maintains line integrity while creating chunks with overlap.
    
    Preserves original line breaks and only splits at line boundaries when possible,
    while still maintaining approximate chunk size targets and configured overlap.
    
    Args:
        chunk_size: Maximum size of chunks (in length_function units)
        chunk_overlap: Overlap between chunks (in length_function units)
        separator: Line separator to use (default: "\n")
        keep_separator: Whether to keep the separator in the chunks
        length_function: Function to calculate length of text (default: len)
    """
    
    def __init__(
        self,
        chunk_size: int = 400,
        chunk_overlap: int = 150,
        separator: str = "\n",
        keep_separator: bool = True,
        length_function: Optional[callable] = None,
    ):
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            keep_separator=keep_separator,
            length_function=length_function,
        )
        self._separator = separator
        self._secondary_separators = ["\n\n", ". ", "! ", "? "]  # Used when line breaks aren't sufficient
        
    def split_text(self, text: str) -> List[str]:
        """
        Split incoming text into chunks while respecting line boundaries.
        
        Args:
            text: The text to split
            
        Returns:
            List of text chunks with appropriate overlap
        """
        if self._chunk_overlap > self._chunk_size:
            raise ValueError(
                f"chunk_overlap ({self._chunk_overlap}) should be smaller than "
                f"chunk_size ({self._chunk_size})"
            )

        # First split by the main separator (usually newlines)
        lines = text.split(self._separator)
        if self._keep_separator:
            lines = [line + self._separator for line in lines[:-1]] + [lines[-1]]
            
        chunks = []
        current_chunk = []
        current_length = 0
        overlap_buffer = []
        
        for line in lines:
            line_length = self._length_function(line)
            
            # If adding this line would exceed the chunk size, finalize current chunk
            if current_length + line_length > self._chunk_size and current_chunk:
                chunks.append("".join(current_chunk))
                
                # Prepare overlap for next chunk
                overlap_buffer = []
                overlap_length = 0
                
                # Add lines from end of current chunk until we reach overlap size
                for overlap_line in reversed(current_chunk):
                    overlap_line_length = self._length_function(overlap_line)
                    if overlap_length + overlap_line_length > self._chunk_overlap:
                        break
                    overlap_buffer.insert(0, overlap_line)
                    overlap_length += overlap_line_length
                
                current_chunk = overlap_buffer
                current_length = overlap_length
            
            current_chunk.append(line)
            current_length += line_length
        
        # Add any remaining text as the final chunk
        if current_chunk:
            chunks.append("".join(current_chunk))
            
        return chunks
    
    def _split_long_line(self, line: str) -> List[str]:
        """
        Handle cases where a single line is longer than the chunk size.
        Falls back to secondary separators and then character-level splitting.
        """
        # First try secondary separators
        for sep in self._secondary_separators:
            if sep in line:
                parts = line.split(sep)
                if self._keep_separator:
                    parts = [part + sep for part in parts[:-1]] + [parts[-1]]
                return parts
                
        # Fall back to character-level splitting
        return [line[i:i+self._chunk_size] for i in range(0, len(line), self._chunk_size)]