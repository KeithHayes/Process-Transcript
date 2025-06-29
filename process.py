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
                f.seek(self.input_pointer)
                self.input_array = f.read()
                self.input_pointer = 0  # pointer for chunk loading
                self.logger.debug(f'Loaded {len(self.input_array)} characters.')
                self.loadchunk(250) # Load first 250 words
                self.formatchunk()
                self.savechunk()

                while True:
                    # Check if we've processed all input
                    if self.input_pointer >= len(self.input_array) and len(self.chunk) <= 0:
                        break
                    
                    self.formatchunk()
                    self.savechunk()
                    
                    # Additional termination condition if no progress is being made
                    if self.output_pointer >= self.textsize:
                        break

            # Write final output to file
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(self.output_array)
                
        except Exception as e:
            self.logger.error(f'Processing failed: {e}', exc_info=True)
            raise

    def loadchunk(self, word_count):
        self.chunk = ""
        words_loaded = 0
        i = self.input_pointer
        # Find first space after the current position
        while i < len(self.input_array) and words_loaded < word_count:
            space_pos = self.input_array.find(' ', i)
            if space_pos == -1:
                self.chunk += self.input_array[i:] # last word
                break
            self.chunk += self.input_array[i:space_pos+1] # add word and space
            words_loaded += 1
            i = space_pos + 1  # Move past space
            
        self.input_pointer = i  # Update pointer to current position
        self.logger.info(f'Loaded {words_loaded} words (total {len(self.chunk)} chars)')
        return self.chunk
    
    def formatchunk(self):
        self.logger.debug(f'Formatting chunk')

    def savechunk(self):
        self.logger.debug(f'Saving chunk (input_pointer={self.input_pointer}, output_pointer={self.output_pointer})')
        try:
            words = []
            current_word = []
            for char in self.chunk:
                if char in (' ', '\n'):
                    if current_word:  # Only add if we have a word
                        words.append(''.join(current_word))
                        current_word = []
                    words.append(char)  # Keep the separator
                else:
                    current_word.append(char)
            if current_word:
                words.append(''.join(current_word))  # Add last word
                
            first_150 = ''.join(words[:150])  # Copy 150 words to output array
            self.output_array += first_150
            self.output_pointer += len(first_150)
            last_100 = ''.join(words[-100:])
            self.chunk = last_100  # move the last 100 words
            
            additional_words = []
            words_added = 0
            i = self.input_pointer
            # Add 150 more words from input array
            while i < len(self.input_array) and words_added < 150:
                space_pos = self.input_array.find(' ', i)
                if space_pos == -1:
                    additional_words.append(self.input_array[i:]) # Add last word
                    break
                    
                additional_words.append(self.input_array[i:space_pos+1])
                words_added += 1
                i = space_pos + 1
            self.chunk += ''.join(additional_words)
            self.input_pointer = i
            
            self.logger.debug(
                f'Updated pointers - input: {self.input_pointer}, output: {self.output_pointer}\n'
                f'First 50 output chars: {self.output_array[:50]}\n'
                f'First 50 new chunk chars: {self.chunk[:50]}'
            )
            
        except Exception as e:
            self.logger.error(f'Save chunk failed: {e}', exc_info=True)
            raise