from difflib import SequenceMatcher
import re
from typing import Optional, Tuple, List

class AlignmentProcessor:
    """Complete text alignment processor with paragraph and sentence awareness."""
    
    def __init__(self, min_match_ratio: float = 0.7, min_context_length: int = 50):
        self.paragraph_splitter = re.compile(r'\n\s*\n')
        self.sentence_splitter = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s')
        self.min_match_ratio = min_match_ratio
        self.min_context_length = min_context_length
        self.min_paragraph_length = 20
        self.default_target_length = 200
    
    def extract_new_content(self, combined: str, context: str) -> str:
        """Extract only new content from combined text,from difflib import SequenceMatcher
import re  # Ensure this exists
from typing import Optional, Tuple, List preserving sentence structure."""
        if not context or len(context) < self.min_context_length:
            return self._capitalize_first(combined)
        
        clean_context = ' '.join(context.split())
        clean_combined = ' '.join(combined.split())
        
        matcher = SequenceMatcher(None, clean_context.lower(), clean_combined.lower())
        match = matcher.find_longest_match(0, len(clean_context), 0, len(clean_combined))
        
        if match.size < len(clean_context) * self.min_match_ratio:
            return self._capitalize_first(combined)
            
        original_pos = len(combined) - len(clean_combined) + match.b + match.size
        new_content = combined[original_pos:].lstrip()
        return self._repair_sentence_boundary(new_content)
    
    def drop_last_paragraph(self, text: str, min_paragraph_length: Optional[int] = None) -> str:
        """Remove incomplete last paragraph if it's too short."""
        min_len = min_paragraph_length or self.min_paragraph_length
        paragraphs = [p for p in self.paragraph_splitter.split(text) if p.strip()]
        
        if len(paragraphs) <= 1:
            return text
            
        if len(paragraphs[-1]) < min_len:
            return text
            
        return '\n\n'.join(paragraphs[:-1]).strip()
    
    def get_tail_for_context(self, text: str, target_length: Optional[int] = None) -> str:
        """Get optimal tail portion of text for context, respecting paragraphs."""
        length = target_length or self.default_target_length
        if len(text) <= length:
            return text
            
        paragraphs = [p for p in self.paragraph_splitter.split(text) if p.strip()]
        
        if len(paragraphs) == 1:
            return text[-length:]
            
        accumulated = []
        current_length = 0
        
        for para in reversed(paragraphs):
            if current_length + len(para) > length and accumulated:
                break
            accumulated.insert(0, para)
            current_length += len(para) + 2  # Account for paragraph breaks
            
        return '\n\n'.join(accumulated)
    
    def find_optimal_cut(self, text: str, original_lines: int) -> Tuple[int, str]:
        """Find best place to cut text based on original line count."""
        lines = text.split('\n')
        avg_lines_per_para = max(1, len(self.paragraph_splitter.split(text)) / len(lines))
        estimated_lines = int(len(lines) * avg_lines_per_para)
        
        if estimated_lines >= original_lines:
            return original_lines, '\n'.join(lines[:original_lines])
        
        # Find nearest paragraph break
        paragraphs = self.paragraph_splitter.split(text)
        line_count = 0
        result = []
        
        for para in paragraphs:
            para_lines = para.count('\n') + 1
            if line_count + para_lines > original_lines:
                break
            result.append(para)
            line_count += para_lines
            
        return line_count, '\n\n'.join(result)
    
    def _capitalize_first(self, text: str) -> str:
        """Ensure proper sentence capitalization."""
        if not text:
            return text
        return text[0].upper() + text[1:] if text else text
    
    def _repair_sentence_boundary(self, text: str) -> str:
        """Fix broken sentences at the boundary."""
        if not text:
            return text
            
        sentences = self.sentence_splitter.split(text)
        if len(sentences) <= 1:
            return text.lstrip()
            
        # Reconstruct with proper spacing
        first_sent = sentences[0].strip()
        remaining = ' '.join(s.strip() for s in sentences[1:])
        
        # Ensure first sentence ends with punctuation
        if first_sent and first_sent[-1] not in {'.', '?', '!'}:
            first_sent += '.'
            
        return f"{first_sent} {remaining}".lstrip()

    def merge_paragraphs(self, paragraphs: List[str]) -> str:
        """Merge processed paragraphs into final text with proper formatting."""
        cleaned = []
        for para in paragraphs:
            p = para.strip()
            if not p:
                continue
                
            # Ensure paragraph ends with punctuation
            if p[-1] not in {'.', '?', '!', '\n'}:
                p += '.'
            cleaned.append(p)
            
        return '\n\n'.join(cleaned)