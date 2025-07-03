import os
import re
import logging
import textwrap
import aiohttp
from config import (CLEANED_FILE, API_URL, API_TIMEOUT, MAX_TOKENS, STOP_SEQUENCES,
                    REPETITION_PENALTY, TEMPERATURE, TOP_P, TOP_T, SENTENCE_MARKER,
                    CHUNK_SIZE, CHUNK_OVERLAP, OUTPUT_CHUNK_SIZE, LOOPCHECK)

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
        self.input_word_pointer = 0
        self.chunk_word_pointer = 0

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
            self.logger.debug(f'Saving chunk (input pointer: {self.input_word_pointer})')
            chunkwords = [word for word in self.chunk.split(' ') if word]

            # Special handling for final chunk
            is_final_chunk = self.input_word_pointer >= len(self.input_array)
            if is_final_chunk:
                save_words = chunkwords  # Save ALL remaining words
                self.logger.debug(f'Final chunk detected - saving all {len(save_words)} words')
                
                # Join with spaces but preserve original formatting (including newlines)
                save_words_string = ' '.join(save_words)
                # Don't add trailing space for final chunk
                self.output_string += save_words_string
                self.output_pointer += len(save_words_string)

                # Clear the chunk as we've processed everything
                self.chunk = ''
            else:
                # Normal chunk processing
                save_words = chunkwords[:OUTPUT_CHUNK_SIZE]
                if save_words:
                    save_words_string = ' '.join(save_words) + ' '
                    self.output_string += save_words_string
                    self.output_pointer += len(save_words_string)
                    
                # Keep overlap if there's more input to process
                remaining_words = chunkwords[OUTPUT_CHUNK_SIZE:] if len(chunkwords) > OUTPUT_CHUNK_SIZE else []
                self.chunk = ' '.join(remaining_words)
                if remaining_words:  # Add space only if there are remaining words
                    self.chunk += ' '
                    
            self.logger.debug(f'Saved {len(save_words)} words. Remaining in chunk: {len(self.chunk.split())}')
            
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
                    raise Exception(error_message)
                
                result = await response.json()
                formatted = result.get("choices", [{}])[0].get("text", "").strip()
                
                if not formatted:
                    error_message = "An empty string is returned."
                    self.logger.error(error_message)
                    raise ValueError(error_message)
                return formatted
                
        except aiohttp.ClientError as e:
            error_message = f"Network or API client error during formatchunk: {str(e)}"
            self.logger.error(error_message, exc_info=True)
            raise ConnectionError(error_message) from e
        except Exception as e:
            error_message = f"An unexpected error occurred during formatchunk: {str(e)}"
            self.logger.error(error_message, exc_info=True)
            raise Exception(error_message) from e

    def deformat(self, formatted_output):
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

    def formatlines(self, unformatted_string):
        """
        Stub implementation for formatting lines of text.
        Currently just returns the input unchanged.
        """
        # TODO: Implement proper formatting logic in next development cycle
        return unformatted_string

    async def process(self, output_file: str):
        if not self._cleaned:
            raise RuntimeError("Must call preprocess() before process()")
            
        self.output_file = output_file
        self.logger.debug(f'Processing to: {self.output_file}')
            
        try:
            with open(CLEANED_FILE, 'r', encoding='utf-8') as f:
                self.input_string = f.read()
                self.logger.info(f'Loaded {len(self.input_string)} chars, {len(self.input_string.split())} words')
                self.input_array = self.input_string.split()
                self.chunk = ""
                self.output_string = ""
                self.input_word_pointer = 0
                self.output_pointer = 0
                
                # Load initial chunk
                self.loadchunk(CHUNK_SIZE)

                while True:
                    if LOOPCHECK:
                        formatted_chunk = self.chunk
                    else:
                        formatted_chunk = await self.formatchunk(self.chunk)
                        sentence_ends_marked = re.sub(r'(?<=[.?!])\s+', SENTENCE_MARKER, formatted_chunk)
                        sentence_starts_marked = re.sub(r'\s+(?=[A-Z])', SENTENCE_MARKER, sentence_ends_marked)
                        self.chunk = self.deformat(sentence_starts_marked)
                    
                    self.savechunk()
                    
                    # Exit condition - check after savechunk to ensure final words processed
                    # is_final_chunk = self.input_word_pointer >= len(self.input_array)
                    if self.input_word_pointer >= len(self.input_array) and not self.chunk.strip():
                        break
                        
                    # Load next chunk if more exists
                    if self.input_word_pointer < len(self.input_array):
                        self.loadchunk(CHUNK_SIZE - CHUNK_OVERLAP)
                
                # Final validation
                input_words = len(self.input_array)
                output_words = len(self.output_string.split())
                self.logger.info(f'Processed {output_words}/{input_words} words')
                
                if input_words != output_words:
                    self.logger.warning(f'Word count mismatch! Input: {input_words}, Output: {output_words}')

                # Process the output string in chunks of 10 lines
                final_output = ''
                lines = self.output_string.split('\n')
                total_lines = len(lines)
                pointer = 0

                while pointer < total_lines:
                    # Get next 10 lines (or remaining lines if less than 10)
                    chunk_lines = lines[pointer:pointer+10]
                    unformatted_string = '\n'.join(chunk_lines)
                    
                    # Format the chunk
                    formatted_string =  self.formatlines(unformatted_string)
                    # Append to final output with newline
                    if final_output:  # Only add newline if not first chunk
                        formatted_string = '\n' + formatted_string
                    final_output += formatted_string
                    pointer += 10
                
                # Write final output
                with open(self.output_file, 'w', encoding='utf-8') as f:
                    #final_output = self.output_string.rstrip()
                    f.write(final_output)
                    self.logger.info(f'Saved {len(final_output)} chars to {self.output_file}')
                    
        except Exception as e:
            self.logger.error(f'Processing failed: {e}', exc_info=True)
            raise