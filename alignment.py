from difflib import SequenceMatcher
import re
from typing import List
from config import MIN_SENTENCE_LENGTH

class AlignmentProcessor:
    """Enhanced text alignment processor with strict sentence handling"""
    
    def __init__(self, min_match_ratio: float = 0.7, min_context_length: int = 50):
        self.sentence_splitter = re.compile(r'(?<=[.!?])\s+')
        self.min_match_ratio = min_match_ratio
        self.min_context_length = min_context_length

    def extract_new_content(self, combined: str, context: str) -> str:
        """Extract only new content while preserving original words"""
        if not context or len(context) < self.min_context_length:
            return self._capitalize_first(combined)
        
        matcher = SequenceMatcher(None, context.lower(), combined.lower())
        match = matcher.find_longest_match(0, len(context), 0, len(combined))
        
        if match.size < len(context) * self.min_match_ratio:
            return self._capitalize_first(combined)
            
        return combined[match.b + match.size:].lstrip()

    def get_tail_for_context(self, text: str, target_length: int) -> str:
        """Get overlapping portion while preserving complete sentences"""
        if not text or target_length <= 0:
            return ""
        
        sentences = []
        current = ""
        for char in text:
            current += char
            if char in {'.', '?', '!'}:
                sentences.append(current.strip())
                current = ""
        
        if current:
            sentences.append(current.strip())
        
        tail = []
        current_length = 0
        for sentence in reversed(sentences):
            if not sentence:
                continue
                
            if current_length + len(sentence) > target_length and tail:
                break
                
            tail.insert(0, sentence)
            current_length += len(sentence) + 1
        
        return ' '.join(tail)

    def _capitalize_first(self, text: str) -> str:
        """Capitalize first letter of text"""
        if not text:
            return text
        return text[0].upper() + text[1:] if text else text

    def validate_sentences(self, text: str) -> List[str]:
        """Validate sentence completeness"""
        errors = []
        sentences = self.sentence_splitter.split(text)
        for i, sentence in enumerate(sentences):
            if len(sentence.split()) < MIN_SENTENCE_LENGTH:
                errors.append(f"Sentence too short at position {i}: '{sentence}'")
            elif sentence[-1] not in {'.', '?', '!'}:
                errors.append(f"Missing ending punctuation: '{sentence}'")
            elif not sentence[0].isupper():
                errors.append(f"Missing starting capitalization: '{sentence}'")
        return errors