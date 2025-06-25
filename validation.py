import re
from typing import List, Tuple

class TranscriptValidator:
    """Validation tools for formatted transcripts"""
    
    def __init__(self):
        self.sentence_pattern = re.compile(
            r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s+'
        )
        self.speaker_pattern = re.compile(
            r'^([A-Z][a-zA-Z\s]+):\s.*$'
        )

    def validate_all(self, text: str) -> Tuple[List[str], List[str]]:
        """Run all validations"""
        return (
            self.validate_sentences(text),
            self.validate_speakers(text)
        )

    def validate_sentences(self, text: str) -> List[str]:
        """Check for complete sentences"""
        errors = []
        sentences = self.sentence_pattern.split(text)
        for i, sent in enumerate(sentences):
            sent = sent.strip()
            if not sent:
                continue
                
            if len(sent.split()) < 3:
                errors.append(f"Sentence too short: '{sent}'")
            elif sent[-1] not in {'.', '?', '!'}:
                errors.append(f"Missing ending punctuation: '{sent}'")
            elif not sent[0].isupper():
                errors.append(f"Missing capitalization: '{sent}'")
                
        return errors

    def validate_speakers(self, text: str) -> List[str]:
        """Check speaker formatting consistency"""
        errors = []
        for i, line in enumerate(text.split('\n')):
            if ':' in line:
                speaker = line.split(':', 1)[0].strip()
                if not self.speaker_pattern.match(line):
                    errors.append(
                        f"Invalid speaker format at line {i}: '{speaker}'"
                    )
        return errors