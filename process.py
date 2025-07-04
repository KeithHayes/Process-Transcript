import os
import re
import logging
import textwrap
import aiohttp
from config import (CLEANED_FILE, API_URL, API_TIMEOUT, MAX_TOKENS, STOP_SEQUENCES, PROCESSED_FILE,
                    REPETITION_PENALTY, TEMPERATURE, TOP_P, TOP_T, SENTENCE_MARKER,
                    CHUNK_SIZE, CHUNK_OVERLAP, OUTPUT_CHUNK_SIZE, FORMATCHECK, LINECHECK)

class ParseFile:
    def __init__(self):
        self.output_pointer = 0
        self.input_string = ""
        self.chunk = ""
        self.output_string = ""
        self._cleaned = False
        self.api_url = API_URL
        self.logger = logging.getLogger(__name__)
        self.session = None
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

            is_final_chunk = self.input_word_pointer >= len(self.input_array)
            if is_final_chunk:
                save_words = chunkwords
                self.logger.debug(f'Final chunk detected - saving all {len(save_words)} words')
                save_words_string = ' '.join(save_words)
                self.output_string += save_words_string
                self.chunk = ''
            else:
                save_words = chunkwords[:OUTPUT_CHUNK_SIZE]
                if save_words:
                    save_words_string = ' '.join(save_words) + ' '
                    self.output_string += save_words_string
                
                remaining_words = chunkwords[OUTPUT_CHUNK_SIZE:] if len(chunkwords) > OUTPUT_CHUNK_SIZE else []
                self.chunk = ' '.join(remaining_words)
                if remaining_words:
                    self.chunk += ' '
                    
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
                    raise Exception(f"API error: {response.status}")
                
                result = await response.json()
                return result.get("choices", [{}])[0].get("text", "").strip()
                
        except Exception as e:
            self.logger.error(f"Formatting failed: {str(e)}", exc_info=True)
            return chunktext

    def deformat(self, formatted_output):
        output = formatted_output.lower()
        output = re.sub(f'[^a-z\\s{re.escape(SENTENCE_MARKER)}]', '', output)
        return output

    def formatlines(self, unformatted_string):
        """
        Stub implementation for formatting lines of text.
        Currently just returns the input unchanged.
        """
        if LINECHECK:
            return_string = unformatted_string
        else:
            # TODO: Implement proper formatting logic in next development cycle
            return_string = unformatted_string
        return return_string

    def preprocess(self, input_file):
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                text = f.read()
                text = re.sub(r'\s+', ' ', text).strip()
            
            os.makedirs(os.path.dirname(CLEANED_FILE) or '.', exist_ok=True)
            with open(CLEANED_FILE, 'w', encoding='utf-8') as f:
                f.write(text)
            
            self._cleaned = True
        except Exception as e:
            self.logger.error(f'Preprocessing failed: {e}', exc_info=True)
            raise

    async def process(self, input_file: str):
        self.preprocess(input_file)
        
        try:
            with open(CLEANED_FILE, 'r', encoding='utf-8') as f:
                self.input_string = f.read()
                self.input_array = self.input_string.split()
                self.chunk = ""
                self.output_string = ""
                self.input_word_pointer = 0
                
                self.loadchunk(CHUNK_SIZE)

                while True:
                    if FORMATCHECK:
                        formatted_chunk = self.chunk
                    else:
                        formatted_chunk = await self.formatchunk(self.chunk)
                        formatted_chunk = re.sub(r'(?<=[.?!])\s+', SENTENCE_MARKER, formatted_chunk)
                        formatted_chunk = re.sub(r'\s+(?=[A-Z])', SENTENCE_MARKER, formatted_chunk)
                        self.chunk = self.deformat(formatted_chunk)
                    
                    self.savechunk()
                    
                    if self.input_word_pointer >= len(self.input_array) and not self.chunk.strip():
                        break
                        
                    if self.input_word_pointer < len(self.input_array):
                        self.loadchunk(CHUNK_SIZE - CHUNK_OVERLAP)
                
                # Process lines through formatlines stub
                final_output = ''
                lines = self.output_string.split('\n')
                total_lines = len(lines)
                pointer = 0

                while pointer < total_lines:
                    chunk_lines = lines[pointer:pointer+10]
                    unformatted_string = '\n'.join(chunk_lines)
                    formatted_string = self.formatlines(unformatted_string)
                    if final_output:
                        formatted_string = '\n' + formatted_string
                    final_output += formatted_string
                    pointer += 10
                
                with open(PROCESSED_FILE, 'w', encoding='utf-8') as f:
                    f.write(final_output)
                    
        except Exception as e:
            self.logger.error(f'Processing failed: {e}', exc_info=True)
            raise