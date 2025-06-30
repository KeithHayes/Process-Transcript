import os
import re
import asyncio
import logging
import textwrap
import aiohttp
from config import (CLEANED_FILE, API_URL, API_TIMEOUT, MAX_TOKENS, STOP_SEQUENCES,
                    REPETITION_PENALTY, TEMPERATURE, TOP_P)

class ParseFile:
    def __init__(self):
        self.input_pointer = 0
        self.output_pointer = 0
        self.input_array = ""
        self.chunk = ""
        self.output_array = ""
        self._cleaned = False
        self.api_url = API_URL
        self.logger = logging.getLogger(__name__)
        self.session = None  # Will hold our aiohttp session

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

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
                i = space_pos + 1
        
        self.input_pointer = i
        new_chunk_part = ''.join(words)
        self.chunk = (self.chunk + new_chunk_part).strip()
        if self.chunk:
            self.chunk += ' '
        self.logger.info(f'Loaded {words_loaded} words (total {len(self.chunk)} chars)')
        return self.chunk
    
    def savechunk(self):
        self.logger.debug(f'Saving chunk (input_pointer={self.input_pointer}, output_pointer={self.output_pointer})')
        try:
            if not self.chunk:
                return

            words = [word for word in self.chunk.split(' ') if word]
            
            # Process first 150 words
            first_150 = words[:150]
            if first_150:
                first_150_text = ' '.join(first_150) + ' '
                self.output_array += first_150_text
                self.output_pointer += len(first_150_text)
            
            # Keep remaining words
            remaining_words = words[150:] if len(words) > 150 else []
            self.chunk = ' '.join(remaining_words)
            if self.chunk:
                self.chunk += ' '
            
            self.logger.debug(f'Updated pointers - input: {self.input_pointer}, output: {self.output_pointer}')
            
        except Exception as e:
            self.logger.error(f'Save chunk failed: {e}', exc_info=True)
            raise

    async def formatchunk(self, chunktext: str) -> str:
            if self.session is None:
                self.session = aiohttp.ClientSession()

            # Store original words for verification, converting to lowercase for a more lenient comparison
            original_words = [word.lower() for word in chunktext.split()]
            
            prompt = textwrap.dedent(f"""\
                Your task is to identify and complete sentences in the provided text by adding necessary punctuation (periods, question marks, exclamation points).
                Crucially, you must preserve ALL original words and their order exactly as they appear in the input text.
                Do NOT add, delete, or modify any words. Do NOT complete partial sentences or rephrase anything.
                Capitalize the first letter of the first word of each complete sentence.
                Leave incomplete sentence fragments exactly as they are, without adding punctuation or capitalization.

                Example:
                Input: "this is a sentence this is another one an incomplete thought"
                Output: "This is a sentence. This is another one. an incomplete thought"

                Text: {chunktext}

                Processed text:""")

            try:
                async with self.session.post(
                    API_URL,
                    json={
                        "prompt": prompt,
                        "max_tokens": 500,
                        "temperature": 0.1,  # Further lower temperature for even more consistency
                        "stop": STOP_SEQUENCES,
                        "repetition_penalty": 1.0,  # Remove penalty as it can encourage slight deviations
                        "top_p": 0.1 # Lower top_p to focus on higher probability tokens
                    },
                    timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
                ) as response:
                    if response.status != 200:
                        self.logger.error(f"API returned non-200 status: {response.status}")
                        return chunktext
                    result = await response.json()
                    formatted = result.get("choices", [{}])[0].get("text", "").strip()
                    
                    # Normalize formatted output for comparison: remove punctuation and convert to lowercase
                    # This makes the word-by-word comparison more robust against capitalization/punctuation differences
                    normalized_formatted_words = re.sub(r'[^\w\s]', '', formatted).lower().split()
                    
                    if normalized_formatted_words != original_words:
                        self.logger.warning("Word mismatch detected after formatting. Returning original text.")
                        self.logger.debug(f"Original words (normalized): {original_words}")
                        self.logger.debug(f"Formatted words (normalized): {normalized_formatted_words}")
                        return chunktext
                    
                    return formatted
                    
            except Exception as e:
                self.logger.error(f"API error during formatchunk: {str(e)}", exc_info=True)
                return chunktext

    def deformat(self, formatted_output):
        # Split at sentence boundaries while preserving original words
        sentences = re.split(r'(?<=[.!?])\s+', formatted_output)
        
        # Join with newlines and clean up
        output = '\n'.join(
            re.sub(r'[.!?]', '', sent).lower().strip()
            for sent in sentences
        )
        
        # Normalize spaces and ensure single newlines
        output = re.sub(r'\s+', ' ', output)
        output = re.sub(r'\n ', '\n', output)
        
        return output.strip()

    def preprocess(self, input_file):
        self.input_file = input_file
        self.logger.debug(f'Preprocessing: {self.input_file}')
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                text = f.read()
                text = re.sub(r'\s+', ' ', text).strip()
                self.textsize = len(text)
            
            os.makedirs(os.path.dirname(CLEANED_FILE) or '.', exist_ok=True)
            with open(CLEANED_FILE, 'w', encoding='utf-8') as f:
                f.write(text)
            
            self._cleaned = True
            self.logger.debug(f'Cleaned file saved: {CLEANED_FILE}')
            
        except Exception as e:
            self.logger.error(f'Preprocessing failed: {e}', exc_info=True)
            raise

    async def process(self, output_file: str):
        if not self._cleaned:
            raise RuntimeError("Must call preprocess() before process()")
        
        self.output_file = output_file
        self.logger.debug(f'Processing to: {self.output_file}')
        
        try:
            with open(CLEANED_FILE, 'r', encoding='utf-8') as f:
                self.input_array = f.read()
                self.logger.info(f'Loaded {len(self.input_array)} characters for processing')
                
                # Initialize processing state
                self.input_pointer = 0
                self.output_pointer = 0
                self.chunk = ""
                self.output_array = ""
                
                # Initial chunk load
                self.loadchunk(250)
                
                # Main processing loop
                while True:
                    # Format current chunk
                    self.chunk = await self.formatchunk(self.chunk)

                    self.logger.info("--- LLM's Raw Formatted Output (single-space separated sentences) ---")

                    self.savechunk()
                    
                    # Check if we're done
                    if self.input_pointer >= len(self.input_array) and not self.chunk.strip():
                        break
                    
                    # Load next chunk if needed
                    remaining_words = self.count_words(self.chunk)
                    if remaining_words < 100 and self.input_pointer < len(self.input_array):
                        self.loadchunk(150)
            
            # Write final output
            with open(self.output_file, 'w', encoding='utf-8') as f:
                final_output = self.output_array.rstrip()
                f.write(final_output)
                self.logger.info(f'Saved {len(final_output)} characters to {self.output_file}')
                
        except Exception as e:
            self.logger.error(f'Processing failed: {e}', exc_info=True)
            raise