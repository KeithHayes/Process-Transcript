import os
import re
import logging

class ParseFile:

    def __init__(self, input_file: str, output_file: str):
        self.input_pointer = 0
        self.output_pointer = 0
        self.input_array = ""
        self.chunk = ""
        self.output_array = ""
        self.input_file = input_file
        self.output_file = output_file
        self._cleaned = False
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f'Files: input={input_file}, output={output_file}')

    def preprocess(self):
        self.logger.info(f'Preprocessing: {self.input_file}')
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                f.seek(self.input_pointer)
                text = f.read()
                text = text.replace('\n', ' ').strip()
                text = re.sub(r' +', ' ', text)
                self.textsize = len(text)
            os.makedirs(os.path.dirname(self.output_file) or '.', exist_ok=True)
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(text)
            self._cleaned = True
            self.logger.debug(f'Cleaned: {self.output_file}')
            
        except Exception as e:
            self.logger.error(f'Preprocessing Error: {e}', exc_info=True)
            raise

    def process(self):
        if not self._cleaned:
            raise RuntimeError("Call preprocess() before process()")
        self.logger.debug(f'Processing: {self.output_file}')
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                self.input_array = f.read()
                self.logger.debug(f'Loaded {len(self.input_array)} characters.')
                
                # Initialize pointers
                self.input_pointer = 0
                self.output_pointer = 0
                
                # Load first chunk (250 words)
                self.loadchunk(250)
                
                while True:
                    # Format and save chunk
                    self.formatchunk()
                    self.savechunk()
                    
                    # Check termination conditions
                    if self.input_pointer >= len(self.input_array) and len(self.chunk) == 0:
                        break
                    
                    # Load next chunk (100 remaining + 150 new words)
                    remaining_words = self.count_words(self.chunk)
                    if remaining_words > 0:
                        # Only load new words if we have input remaining
                        if self.input_pointer < len(self.input_array):
                            self.loadchunk(150)
                        else:
                            # No more input, just process remaining words
                            self.chunk = self.chunk.strip()
                            if len(self.chunk) == 0:
                                break

            # Write final output to file
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(self.output_array)
                
        except Exception as e:
            self.logger.error(f'Processing failed: {e}', exc_info=True)
            raise

    def count_words(self, text):
        return len(text.split()) if text.strip() else 0

    def loadchunk(self, word_count):
        words_loaded = 0
        words = []
        i = self.input_pointer
        
        while i < len(self.input_array) and words_loaded < word_count:
            space_pos = self.input_array.find(' ', i)
            if space_pos == -1:  # Last word in input
                word = self.input_array[i:]
                words.append(word + ' ')
                words_loaded += 1
                i = len(self.input_array)
                break
            else:
                word = self.input_array[i:space_pos+1]
                words.append(word)
                words_loaded += 1
                i = space_pos + 1  # Move past space
        
        self.input_pointer = i
        new_chunk_part = ''.join(words)
        self.chunk = (self.chunk + new_chunk_part).strip()
        self.logger.info(f'Loaded {words_loaded} words (total {len(self.chunk)} chars)')
        return self.chunk
    
    def formatchunk(self):
        self.logger.debug(f'Formatting chunk')

    def savechunk(self):
        self.logger.debug(f'Saving chunk (input_pointer={self.input_pointer}, output_pointer={self.output_pointer})')
        try:
            words = self.chunk.split(' ')
            # Filter out empty strings from split
            words = [word for word in words if word]
            
            # Take first 150 words (or all if less than 150)
            first_150 = words[:150]
            first_150_text = ' '.join(first_150) + ' '
            self.output_array += first_150_text
            self.output_pointer += len(first_150_text)
            
            # Keep remaining words (should be 100 in normal case)
            remaining_words = words[150:] if len(words) > 150 else []
            self.chunk = ' '.join(remaining_words)
            
            self.logger.debug(
                f'Updated pointers - input: {self.input_pointer}, output: {self.output_pointer}\n'
                f'First 50 output chars: {self.output_array[:50]}\n'
                f'First 50 new chunk chars: {self.chunk[:50]}'
            )
            
        except Exception as e:
            self.logger.error(f'Save chunk failed: {e}', exc_info=True)
            raise