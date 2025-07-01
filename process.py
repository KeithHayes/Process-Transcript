import os
import re
import logging
import textwrap
import aiohttp
from config import (CLEANED_FILE, API_URL, API_TIMEOUT, MAX_TOKENS, STOP_SEQUENCES,
                    REPETITION_PENALTY, TEMPERATURE, TOP_P, TOP_T, SENTENCE_MARKER)

class ParseFile:
    def __init__(self):
        self.output_pointer = 0
        self.input_string = ""
        self.chunk = ""
        self.output_string = ""
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
        while words_loaded < word_count and self.input_word_pointer < len(self.input_array):
            words.append(self.input_array[self.input_word_pointer])
            self.input_word_pointer += 1
            words_loaded += 1

        wordschunk = ' '.join(words)
        self.chunk = (self.chunk + wordschunk).strip()
        if self.chunk:
            self.chunk += ' '
        self.logger.info(f'Loaded {words_loaded} words (total {len(self.chunk)} chars)')
        return self.chunk
    
    def savechunk(self):
        try:
            if not self.chunk:
                return
            self.logger.debug(f'Saving chunk')
            target_pointer = self.output_pointer
            chunkwords = [word for word in self.chunk.split(' ') if word]
            save_words = chunkwords[:150]                                   # First 150 words of chunk of chunk or fewer
            if save_words:
                save_words_string = ' '.join(save_words) + ' '              # Join with spaces, add space at end
                self.output_string += save_words_string
                self.output_pointer += len(save_words_string)
            
            remaining_words = chunkwords[150:] if len(chunkwords) > 150 else []
            remaining_words_string = ' '.join(remaining_words)
            remaining_words_string = re.sub(r"[\.!?](?!.*[\.!?])", '', remaining_words_string)
            remaining_words_string = re.sub(r"[A-Z](?!.*[A-Z])", '', remaining_words_string)
            self.chunk = remaining_words_string + ' '
            
            self.logger.debug(f'Saving chunk at: {target_pointer}, length: {self.output_pointer - target_pointer} characters')
        except Exception as e:
            self.logger.error(f'Save of chunk failed: {e}', exc_info=True)
            raise

    async def formatchunk(self, chunktext: str) -> str:
        if self.session is None:
            self.session = aiohttp.ClientSession()
        
        prompt = textwrap.dedent(f"""\
            MUST maintain the EXACT original words and their order.
            MUST NOT add, delete, or change any words.
            MUST NOT rephrase or summarize.
            Add periods, question marks, or exclamation points to puntuate complete sentences.
            Capitalize the first letter of the first word of each complete sentence.
            Incomplete sentence fragments must remain as they are, without any added punctuation or capitalization change.
            No puntuation capitalization or word changes after the first word or before the last word in a sentence.
            Only the first letteer in a sentence can be uppercase.

            Text: {chunktext}

            Formatted text:""")

        try:
            async with self.session.post(
                API_URL,
                json={
                    "prompt": prompt,
                    "max_tokens": MAX_TOKENS,
                    "temperature": TEMPERATURE,
                    "stop": STOP_SEQUENCES,
                    "repetition_penalty": REPETITION_PENALTY,
                    "top_p": TOP_P,
                    "top_t": TOP_T
                },
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
            ) as response:
                if response.status != 200:
                    error_message = f"API returned non-200 status: {response.status}. Response: {await response.text()}"
                    self.logger.error(error_message)
                    raise Exception(error_message) # Error: API response incorrect
                
                result = await response.json()
                formatted = result.get("choices", [{}])[0].get("text", "").strip()
                
                if not formatted:
                    error_message = "An empty string is returned."
                    self.logger.error(error_message)
                    raise ValueError(error_message) # Error: LLM returned empty string
                return formatted
                
        except aiohttp.ClientError as e:
            error_message = f"Network or API client error during formatchunk: {str(e)}"
            self.logger.error(error_message, exc_info=True)
            raise ConnectionError(error_message) from e # Error: Cannot connect to LLM API
        except Exception as e:
            error_message = f"An unexpected error occurred during formatchunk: {str(e)}"
            self.logger.error(error_message, exc_info=True)
            raise Exception(error_message) from e # Catch any other unexpected errors

    def deformat(self, formatted_output):
        # remove all special characters.  Only lowercase letters, spaces, and the special character will remain.
        output = formatted_output.lower()
        output = re.sub(f'[^a-z\\s{re.escape(SENTENCE_MARKER)}]', '', output)
        return output

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
                self.input_string = f.read()
                self.logger.info(f'Loaded {len(self.input_string)} character string')
                self.input_array = self.input_string.split()
                self.chunk_array = ""
                self.output_array = ""
                self.chunk = ""
                self.output_string = ""
                self.input_word_pointer = 0
                self.chunk_word_pointer = 0
                self.output_pointer = 0
                self.loadchunk(250)     # first chunk

                LOOPCHECK = False

                while True:
                    if LOOPCHECK:
                        formatted_chunk = self.chunk
                    else:
                        formatted_chunk = await self.formatchunk(self.chunk)                                    # Format
                    sentence_ends_marked = re.sub(r'(?<=[.?!])\s+', SENTENCE_MARKER, formatted_chunk)           # Mark sentence ends
                    sentence_starts_marked = re.sub(r'\s+(?=[A-Z])', SENTENCE_MARKER, sentence_ends_marked)     # Mark sentence starts
                    self.chunk = self.deformat(sentence_starts_marked)
                    self.savechunk()
                    if self.input_word_pointer >= len(self.input_array):                                        # End of input
                        break
                    self.loadchunk(150)                                                                         # Load next chunk

                # Flush words in chunk
                if self.chunk.strip():
                    if LOOPCHECK:
                        formatted_chunk = self.chunk
                    else:
                        formatted_chunk = await self.formatchunk(self.chunk)
                    sentence_ends_marked = re.sub(r'(?<=[.?!])\s+', SENTENCE_MARKER, formatted_chunk)
                    sentence_starts_marked = re.sub(r'\s+(?=[A-Z])', SENTENCE_MARKER, sentence_ends_marked)
                    self.chunk = self.deformat(sentence_starts_marked)
                    self.savechunk()
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                final_output = self.output_string.rstrip()                                                      # Write output
                f.write(final_output)
                self.logger.info(f'Saved {len(final_output)} characters to {self.output_file}')
                
        except Exception as e:
            self.logger.error(f'File not marked: {e}', exc_info=True)
            raise