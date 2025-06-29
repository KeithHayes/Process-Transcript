import os
import re
import logging

class ParseFile:
    input_pointer = 0
    output_pointer = 0
    input_array = []
    chunk = []
    output_array = []

    def __init__(self, input_file: str, output_file: str):
        self.input_file = input_file
        self.output_file = output_file
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f'Files: input={input_file}, output={output_file}')
        self._cleaned = False

    def preprocess(self):
        self.logger.info(f'Preprocessing: {self.input_file}')
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                f.seek(ParseFile.input_pointer)
                text = f.read()
                text = text.replace('\n', ' ').strip()
                text = re.sub(r' +', ' ', text)
            os.makedirs(os.path.dirname(self.output_file) or '.', exist_ok=True)
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(text)
            self._cleaned = True
            self.logger.debug(f'Output: {self.output_file}')
            
        except Exception as e:
            self.logger.error(f'Preprocessing Error: {e}', exc_info=True)
            raise

    def process(self):
        if not self._cleaned:
            raise RuntimeError("Call preprocess() before process()")
        self.logger.debug(f'Processing: {self.output_file}')
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                f.seek(ParseFile.input_pointer)
                ParseFile.input_array = list(f.read())
                ParseFile.input_pointer = 0  # Reset pointer for chunk loading
                self.logger.info(f'Loaded {len(ParseFile.input_array)} characters.')
                self.logger.debug(f'First 20 chars: {ParseFile.input_array[:20]}')
                # Load first 250 words
                self.loadchunk(250)
                self.formatchunk()
                self.savechunk()

                
                
        except Exception as e:
            self.logger.error(f'Processing failed: {e}', exc_info=True)
            raise

    def loadchunk(self, word_count):
        self.chunk = []
        words_loaded = 0
        i = ParseFile.input_pointer
        
        while i < len(ParseFile.input_array) and words_loaded < word_count:
            # Find next space starting from current position
            try:
                space_pos = ParseFile.input_array.index(' ', i)
            except ValueError:
                # No more spaces, take remaining characters as last word
                self.chunk.extend(ParseFile.input_array[i:])
                break
                
            # Include the word and its trailing space
            self.chunk.extend(ParseFile.input_array[i:space_pos+1])
            words_loaded += 1
            i = space_pos + 1  # Move past this space
            
        ParseFile.input_pointer = i  # Update pointer to current position
        self.logger.info(f'Loaded {words_loaded} words (total {len(self.chunk)} chars)')
        #self.logger.debug(f'Chunk preview: {"".join(self.chunk[:50])}...')
        #self.logger.debug(f'Chunk tail: ...{"".join(self.chunk[-50:])}')
        return self.chunk
    
    def formatchunk(self):
        self.logger.debug(f'Formatting chunk')
        # as a result of formatting linefeeds have been added to the content of the chunk

    def savechunk(self):
        self.logger.debug(f'Saving chunk (input_pointer={self.input_pointer}, output_pointer={self.output_pointer})')
        try:
            chunk_text = ''.join(self.chunk) # Convert chunk to string
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
            if current_word:  # Add last word if exists
                words.append(''.join(current_word))
                
            # Copy first 150 words to output array
            first_150 = words[:150]
            self.output_array.extend(first_150)
            self.output_pointer += len(''.join(first_150))
            
            # Copy last 100 words to beginning of chunk (simple array operation)
            last_100 = words[-100:]
            self.chunk = last_100
            
            # Add 150 more words from input array
            additional_words = []
            words_added = 0
            i = self.input_pointer
            
            while i < len(self.input_array) and words_added < 150:
                try:
                    space_pos = self.input_array.index(' ', i)
                    additional_words.extend(self.input_array[i:space_pos+1])
                    words_added += 1
                    i = space_pos + 1
                except ValueError:
                    additional_words.extend(self.input_array[i:]) # Handle last word
                    break
                    
            self.chunk.extend(additional_words)
            self.input_pointer = i
            
            self.logger.debug(
                f'Updated pointers - input: {self.input_pointer}, output: {self.output_pointer}\n'
                f'First 3 output words: {self.output_array[:3]}\n'
                f'First 3 new chunk words: {self.chunk[:3]}'
            )
            
        except Exception as e:
            self.logger.error(f'Save chunk failed: {e}', exc_info=True)
            raise

