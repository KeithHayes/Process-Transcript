import os
import re
import logging
import textwrap
import aiohttp
from config import (CLEANED_FILE, API_URL, API_TIMEOUT, MAX_TOKENS, STOP_SEQUENCES,
                    REPETITION_PENALTY, TEMPERATURE, TOP_P, TOP_T, SENTENCE_MARKER,
                    CHUNK_SIZE, CHUNK_OVERLAP, OUTPUT_CHUNK_SIZE, FORMATCHECK, 
                    PROCESSED_FILE, POSTPROCESSED_FILE, LINECHECK)

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
        self.chunk = (self.chunk + ' ' + wordschunk).strip()
        if self.chunk:
            self.chunk += ' '
        self.logger.info(f'Loaded {words_loaded} words (total {len(self.chunk)} chars)')
        return self.chunk
    
    def savechunk(self):
        try:
            if not self.chunk.strip():
                return
                
            self.logger.debug(f'Saving chunk (input pointer: {self.input_word_pointer})')
            chunkwords = self.chunk.split()
            
            # Check if this is the final chunk
            is_final_chunk = (self.input_word_pointer >= len(self.input_array) and 
                             len(chunkwords) <= (CHUNK_OVERLAP + OUTPUT_CHUNK_SIZE))
            
            if is_final_chunk:
                # For final chunk, save all remaining words
                save_words = chunkwords
                self.logger.debug(f'Final chunk detected - saving all {len(save_words)} words')
                
                save_words_string = ' '.join(save_words)
                self.output_string += save_words_string
                self.output_pointer += len(save_words_string)
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
                if remaining_words:
                    self.chunk += ' '
                    
            self.logger.debug(f'Saved {len(save_words)} words. Remaining in chunk: {len(self.chunk.split())}')
            
        except Exception as e:
            self.logger.error(f'Save of chunk failed: {e}', exc_info=True)
            raise

    async def formatchunk(self, chunktext: str) -> str:
        if self.session is None:
            self.session = aiohttp.ClientSession()
        
        # Handle protected chunks
        is_protected_chunk = chunktext.startswith("[CONTINUATION:") and chunktext.endswith(":END]")
        if is_protected_chunk:
            chunktext = chunktext[14:-5].strip()

        prompt = textwrap.dedent(f"""\
            MUST maintain the EXACT original words and their order.
            MUST NOT add, delete, or change any words.
            MUST NOT rephrase or summarize.
            {"THIS IS A FINAL FRAGMENT - ONLY ADD BASIC PUNCTUATION IF APPROPRIATE" if is_protected_chunk else ""}
            Add periods, question marks, or exclamation points to punctuate complete sentences.
            Capitalize the first letter of the first word of each complete sentence.
            Incomplete sentence fragments must remain as they are.
            No punctuation, capitalization or word changes after the first word or before the last word in a sentence.
            Only the first letter in a sentence can be uppercase.

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
                    error_message = "Empty response from API"
                    self.logger.error(error_message)
                    raise ValueError(error_message)
                    
                # Reapply protective markers if needed
                if is_protected_chunk:
                    formatted = f"[CONTINUATION: {formatted} :END]"
                    
                return formatted
                
        except aiohttp.ClientError as e:
            error_message = f"Network error during formatchunk: {str(e)}"
            self.logger.error(error_message, exc_info=True)
            raise ConnectionError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error in formatchunk: {str(e)}"
            self.logger.error(error_message, exc_info=True)
            raise Exception(error_message) from e

    def deformat(self, formatted_output):
        output = formatted_output.lower()
        output = output.replace("[continuation:", "").replace(":end]", "")
        output = re.sub(f'[^a-z\\s{re.escape(SENTENCE_MARKER)}]', '', output)
        return output

    async def formatlines(self, unformatted_string):
        if LINECHECK:
            return unformatted_string

        if self.session is None:
            self.session = aiohttp.ClientSession()

        lines = unformatted_string.split('\n')
        formatted_lines = []
        
        for line in lines:
            if not line.strip():
                formatted_lines.append('')
                continue
                
            try:
                prompt = textwrap.dedent(f"""\
                    MUST maintain the EXACT original words and their order.
                    MUST NOT add, delete, or change any words.
                    MUST NOT rephrase or summarize.
                    Add periods, question marks, or exclamation points to punctuate complete sentences.
                    Capitalize the first letter of the first word of each complete sentence.
                    Incomplete sentence fragments must remain as they are.
                    Only add punctuation at the end if appropriate.
                    Only capitalize the first word if it starts a sentence.

                    Text: {line}

                    Formatted text:""")

                async with self.session.post(
                    self.api_url,
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
                        error_message = f"API error: {response.status}. Response: {await response.text()}"
                        self.logger.error(error_message)
                        formatted_lines.append(line)
                        continue
                    
                    result = await response.json()
                    formatted_line = result.get("choices", [{}])[0].get("text", "").strip()
                    
                    if not formatted_line:
                        self.logger.warning(f"Empty response for line: {line}")
                        formatted_lines.append(line)
                    else:
                        formatted_lines.append(formatted_line)
                        
            except Exception as e:
                self.logger.error(f"Error formatting line: {line}. Error: {str(e)}", exc_info=True)
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)

    def preprocess(self, input_file):
        self.input_file = input_file
        self.logger.debug(f'Preprocessing: {self.input_file}')
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                text = f.read()
                text = re.sub(r'\s+', ' ', text).strip()
                self.textsize = len(text)
            self._cleaned = True
            self.logger.debug(f'Cleaned text size: {self.textsize} chars')
            return text
        except Exception as e:
            self.logger.error(f'Preprocessing failed: {e}', exc_info=True)
            raise

    async def process(self, input_file: str):
        self.input_string = self.preprocess(input_file)
        if not self._cleaned:
            raise RuntimeError("Must call preprocess() before process()")
            
        self.logger.info(f'Processing {len(self.input_string)} chars')
            
        try:
            self.input_array = self.input_string.split()
            self.chunk = ""
            self.output_string = ""
            self.input_word_pointer = 0
            self.output_pointer = 0
            
            # Load initial chunk
            self.loadchunk(CHUNK_SIZE)

            while True:
                if FORMATCHECK:
                    formatted_chunk = self.chunk
                else:
                    formatted_chunk = await self.formatchunk(self.chunk)
                    sentence_ends_marked = re.sub(r'(?<=[.?!])\s+', SENTENCE_MARKER, formatted_chunk)
                    sentence_starts_marked = re.sub(r'\s+(?=[A-Z])', SENTENCE_MARKER, sentence_ends_marked)
                    self.chunk = self.deformat(sentence_starts_marked)
                
                self.savechunk()
                
                # Exit condition
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
                missing = input_words - output_words
                self.logger.warning(f'Word count mismatch! Missing {missing} words')
                self.logger.debug(f'Last input words: {" ".join(self.input_array[-20:])}')
                self.logger.debug(f'Last output words: {" ".join(self.output_string.split()[-20:])}')

            # Save processed output
            with open(PROCESSED_FILE, 'w', encoding='utf-8') as f:
                clean_output = self.output_string.replace("[CONTINUATION:", "").replace(":END]", "")
                f.write(clean_output)
                self.logger.info(f'Saved processed output to {PROCESSED_FILE}')

            # Process lines in batches
            final_output = ''
            lines = clean_output.split('\n')
            total_lines = len(lines)
            pointer = 0

            while pointer < total_lines:
                chunk_lines = lines[pointer:pointer+10]
                unformatted_string = '\n'.join(chunk_lines)
                formatted_string = await self.formatlines(unformatted_string)
                if final_output:
                    formatted_string = '\n' + formatted_string
                final_output += formatted_string
                pointer += 10
                self.logger.info(f'Processed {pointer}/{total_lines} lines')
            
            # Save final output
            with open(POSTPROCESSED_FILE, 'w', encoding='utf-8') as f:
                f.write(final_output)
                self.logger.info(f'Saved final output to {POSTPROCESSED_FILE}')
                
        except Exception as e:
            self.logger.error(f'Processing failed: {e}', exc_info=True)
            raise