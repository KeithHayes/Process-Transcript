from difflib import SequenceMatcher
import re
from typing import Optional, Tuple, List, Dict

class AlignmentProcessor:
    """Enhanced text alignment processor with strict sentence and speaker handling"""
    
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
        """Enhanced content extraction with sentence validation"""
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
        
        return self._repair_sentence_boundary(
            self._normalize_speakers(new_content)
        )

    def get_tail_for_context(self, text: str, target_length: int = 200) -> str:
        """Extract the tail end of text for context in next chunk processing."""
        if not text or target_length <= 0:
            return ""
        
        # Split into sentences first to maintain sentence boundaries
        sentences = self.sentence_splitter.split(text)
        if not sentences:
            return ""
        
        # Work backwards to find enough content
        tail = []
        current_length = 0
        for sentence in reversed(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Ensure sentence ends with punctuation
            if sentence[-1] not in {'.', '?', '!'}:
                sentence += '.'
                
            if current_length + len(sentence) > target_length and tail:
                break
                
            tail.insert(0, sentence)
            current_length += len(sentence) + 1  # +1 for space
        
        return ' '.join(tail)

    def _normalize_speakers(self, text: str) -> str:
        """Ensure consistent speaker formatting"""
        lines = []
        for line in text.split('\n'):
            match = self.speaker_detector.match(line)
            if match:
                speaker = match.group('speaker').strip().title()
                content = match.group('content').strip()
                lines.append(self.speaker_format.format(name=speaker, content=content))
            else:
                lines.append(line)
        return '\n'.join(lines)

    def _repair_sentence_boundary(self, text: str) -> str:
        """Fix broken sentences and punctuation"""
        sentences = []
        for sentence in self.sentence_splitter.split(text):
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Ensure proper ending
            if sentence[-1] not in {'.', '?', '!'}:
                sentence += '.'
            # Ensure proper capitalization
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
            if len(sentence.split()) < 3:  # Too short
                errors.append(f"Sentence too short at position {i}: '{sentence}'")
            elif sentence[-1] not in {'.', '?', '!'}:
                errors.append(f"Missing ending punctuation: '{sentence}'")
        return errors