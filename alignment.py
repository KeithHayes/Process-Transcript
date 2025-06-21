from difflib import SequenceMatcher
import re
from typing import Optional, Tuple

class AlignmentProcessor:
    """Handles alignment between original and formatted text with paragraph awareness."""
    
    def __init__(self, min_match_ratio: float = 0.7, min_context_length: int = 50):
        """
        Args:
            min_match_ratio: Minimum similarity ratio (0-1) to consider a context match valid
            min_context_length: Minimum length of context to attempt matching against
        """
        self.paragraph_splitter = re.compile(r'\n\s*\n')
        self.min_match_ratio = min_match_ratio
        self.min_context_length = min_context_length
    
    def extract_new_content(self, combined: str, context: str) -> str:
        """
        Identify and extract only the new content from LLM output.
        Uses fuzzy matching to handle rephrasing in the context portion.
        
        Args:
            combined: Full LLM output (context + new content)
            context: Previous context we expect to find at the start
            
        Returns:
            Just the new content portion
        """
        if not context or len(context) < self.min_context_length:
            return combined
        
        # Normalize whitespace for better matching
        clean_context = ' '.join(context.split())
        clean_combined = ' '.join(combined.split())
        
        matcher = SequenceMatcher(None, clean_context.lower(), clean_combined.lower())
        match = matcher.find_longest_match(0, len(clean_context), 0, len(clean_combined))
        
        # Verify match quality
        if match.size < len(clean_context) * self.min_match_ratio:
            return combined  # Fallback if we can't find good alignment
            
        # Get the position in original (non-normalized) combined text
        # This is approximate but works well enough for our purposes
        original_pos = len(combined) - len(clean_combined) + match.b + match.size
        return combined[original_pos:].lstrip()
    
    def drop_last_paragraph(self, text: str, min_paragraph_length: int = 20) -> str:
        """
        Remove the last paragraph from the text if it exists.
        
        Args:
            text: Input text
            min_paragraph_length: Minimum length to consider as a paragraph
            
        Returns:
            Text with last paragraph removed if it meets criteria
        """
        paragraphs = [p for p in self.paragraph_splitter.split(text) if p.strip()]
        
        if len(paragraphs) <= 1:
            return text
            
        # Don't drop very short paragraphs (might be headers/separators)
        if len(paragraphs[-1]) < min_paragraph_length:
            return text
            
        return '\n\n'.join(paragraphs[:-1])
    
    def get_tail_for_context(self, text: str, target_length: int = 200) -> str:
        """
        Get the ending portion of text to use as context for next chunk.
        Tries to end at paragraph boundaries when possible.
        
        Args:
            text: Input text
            target_length: Approximate desired length
            
        Returns:
            The tail portion of the text best suited for context
        """
        if len(text) <= target_length:
            return text
            
        paragraphs = [p for p in self.paragraph_splitter.split(text) if p.strip()]
        
        # Case 1: Single paragraph - just take the end
        if len(paragraphs) == 1:
            return text[-target_length:]
            
        # Case 2: Find optimal paragraph break
        accumulated = []
        current_length = 0
        
        for para in reversed(paragraphs):
            if current_length + len(para) > target_length and accumulated:
                break
            accumulated.insert(0, para)
            current_length += len(para) + 2  # Account for paragraph breaks
            
        return '\n\n'.join(accumulated)
    
    def find_optimal_cut(self, text: str, original_lines: int) -> Tuple[int, str]:
        """
        Advanced method to find the best place to cut formatted text
        to align with original line count progress.
        
        Args:
            text: Formatted text
            original_lines: Number of original lines processed so far
            
        Returns:
            Tuple of (estimated_lines_covered, optimal_substring)
        """
        # This is a more sophisticated version that would use:
        # 1. Line count estimation
        # 2. Semantic similarity
        # 3. Structural analysis
        # Implementation would depend on your specific requirements
        
        # Placeholder implementation - would need customization
        avg_lines_per_paragraph = 5  # Example value
        estimated_lines = len(text.split('\n')) * avg_lines_per_paragraph
        return min(estimated_lines, original_lines), text