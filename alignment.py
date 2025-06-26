from difflib import SequenceMatcher
import re
from typing import Optional, Tuple, List, Dict

class AlignmentProcessor:
    """Enhanced text alignment processor with strict sentence handling"""
    
    def __init__(self, min_match_ratio: float = 0.7, min_context_length: int = 50):
        self.paragraph_splitter = re.compile(r'\n\s*\n')
        self.sentence_splitter = re.compile(
            r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s+'
        )
        self.speaker_detector = re.compile(
            r'^(?P<speaker>[A-Z][a-zA-Z\s]+):\s*(?P<content>.*)$'
        )
        self.min_match_ratio = min_match_ratio
        self.min_context_length = min_context_length
        self.min_sentence_length = 20
        self.speaker_format = "{name}: {content}"

    def extract_new_content(self, combined: str, context: str) -> str:
        """Extract only new content while preserving sentence boundaries"""
        if not context or len(context) < self.min_context_length:
            return self._capitalize_first(combined)
        
        matcher = SequenceMatcher(None, context.lower(), combined.lower())
        match = matcher.find_longest_match(0, len(context), 0, len(combined))
        
        if match.size < len(context) * self.min_match_ratio:
            return self._capitalize_first(combined)
            
        original_pos = len(combined) - len(context) + match.b + match.size
        new_content = combined[original_pos:].lstrip()
        
        return self._repair_sentence_boundary(new_content)

    def get_tail_for_context(self, text: str, target_length: int = 200) -> str:
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
                
            if not sentence[0].isupper():
                sentence = sentence[0].upper() + sentence[1:]
            if sentence[-1] not in {'.', '?', '!'}:
                sentence += '.'
                
            if current_length + len(sentence) > target_length and tail:
                break
                
            tail.insert(0, sentence)
            current_length += len(sentence) + 1
        
        return ' '.join(tail)

    def _repair_sentence_boundary(self, text: str) -> str:
        """Ensure proper sentence formatting"""
        sentences = []
        for sentence in self.sentence_splitter.split(text):
            sentence = sentence.strip()
            if not sentence:
                continue
            if sentence[-1] not in {'.', '?', '!'}:
                sentence += '.'
            sentences.append(sentence[0].upper() + sentence[1:])
            
        return ' '.join(sentences)

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
            if len(sentence.split()) < 3:
                errors.append(f"Sentence too short at position {i}: '{sentence}'")
            elif sentence[-1] not in {'.', '?', '!'}:
                errors.append(f"Missing ending punctuation: '{sentence}'")
            elif not sentence[0].isupper():
                errors.append(f"Missing starting capitalization: '{sentence}'")
        return errors