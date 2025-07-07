import os
import re
import logging
import textwrap
import aiohttp
import shutil
from config import (API_URL, API_TIMEOUT, MAX_TOKENS, STOP_SEQUENCES,
                    REPETITION_PENALTY, TEMPERATURE, TOP_P, TOP_T, SENTENCE_MARKER,
                    CHUNK_SIZE, CHUNK_OVERLAP, OUTPUT_CHUNK_SIZE, FORMATCHECK, 
                    PROCESSED_FILE, POSTPROCESSED_FILE, LINECHECK, SAVEDCHUNKS)

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
        self.logger.info(f'Loaded {words_loaded} words (input pointer: {self.input_word_pointer})')
        return self.chunk
    
    def savechunk(self):
        try:
            if not self.chunk:
                return
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

        except Exception as e:
            self.logger.error(f'Save of chunk failed: {e}', exc_info=True)
            raise

    async def formatchunk(self, chunktext: str) -> str:
        if self.session is None:
            self.session = aiohttp.ClientSession()
        
        prompt = textwrap.dedent(f"""\
            Your task is to reformat the provided text.
            Strictly adhere to the following rules:
            - Maintain the EXACT original words and their order.
            - NEVER add, delete, rephrase, or summarize any words.
            - Put each complete sentence on its own line.
            - Do NOT merge sentences together.
            - Do NOT let proper names end sentences if they are part of an ongoing thought.
            - Add proper punctuation (periods, question marks, exclamation points) to complete sentences only at their end.
            - Capitalize the first word of each complete sentence.
            - Leave incomplete fragments as-is on their own line.
            - ONLY output the reformatted text. DO NOT include any additional commentary, explanations, or instructions.
            - Ensure there are no extra spaces before or after any punctuation mark.

            Example:
            Input: "the cat sat the dog ran"
            Output: "The cat sat.\nThe dog ran."

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
                    return chunktext
                
                result = await response.json()
                formatted = result.get("choices", [{}])[0].get("text", "").strip()
                return formatted if formatted else chunktext
                
        except Exception as e:
            self.logger.error(f"Error formatting chunk: {str(e)}")
            return chunktext

    def deformat(self, formatted_output):
        # First protect existing newlines
        protected = formatted_output.replace('\n', SENTENCE_MARKER)
        # Then process normally
        output = protected.lower()
        output = re.sub(f'[^a-z\\s{re.escape(SENTENCE_MARKER)}]', '', output)
        # Restore newlines
        return output.replace(SENTENCE_MARKER, '\n')

    async def formatlines(self, unformatted_string):
        """
        Formats lines of text by sending each line to the LLM API for proper punctuation and capitalization.
        Maintains original words and order while adding appropriate punctuation and capitalization.
        
        Args:
            unformatted_string: Input string with one sentence per line
        
        Returns:
            Formatted string with proper punctuation and capitalization
        """
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
                    Your task is to punctuate and capitalize the provided line of text.
                    Strictly adhere to the following rules:
                    - Maintain the EXACT original words and their order.
                    - NEVER add, delete, rephrase, or summarize any words.
                    - Add periods, question marks, or exclamation points to punctuate complete sentences only at their end.
                    - Capitalize the first letter of the first word of each complete sentence.
                    - Incomplete sentence fragments must remain as they are, without added punctuation or capitalization unless they are a proper noun.
                    - Only add punctuation at the very end of a complete sentence.
                    - Only capitalize the first word if it starts a sentence.
                    - ONLY output the reformatted text. DO NOT include any additional commentary, explanations, or instructions.
                    - Ensure there are no extra spaces before or after any punctuation mark.

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
                        error_message = f"API returned non-200 status: {response.status}. Response: {await response.text()}"
                        self.logger.error(error_message)
                        formatted_lines.append(line)  # Fall back to original line if API fails
                        continue
                    
                    result = await response.json()
                    formatted_line = result.get("choices", [{}])[0].get("text", "").strip()
                    
                    if not formatted_line:
                        self.logger.warning(f"Empty response for line: {line}")
                        formatted_lines.append(line)  # Fall back to original line if empty response
                    else:
                        formatted_lines.append(formatted_line)
                        
            except Exception as e:
                self.logger.error(f"Error formatting line: {line}. Error: {str(e)}", exc_info=True)
                formatted_lines.append(line)  # Fall back to original line on error
        
        return '\n'.join(formatted_lines)

    def preprocess(self, input_file):
            self.input_file = input_file
            self.logger.debug(f'Preprocessing: {self.input_file}')
            try:
                with open(self.input_file, 'r', encoding='utf-8') as f:
                    text = f.read()

                # Normalize smart apostrophes and quotes to ASCII
                text = text.replace("’", "'").replace("“", '"').replace("”", '"')
                text = text.replace("—", " -- ") # Normalize em-dashes to spaces or consistent markers

                # Replace all non-alphanumeric, non-apostrophe, non-hyphen characters with spaces.
                # This is a more robust way to handle punctuation.
                # Keep letters, numbers, hyphens, and apostrophes within words.
                # Everything else becomes a space.
                text = re.sub(r"[^A-Za-z0-9'\-]+", " ", text)

                # Normalize all whitespace (including multiple spaces from previous step) to single spaces
                text = re.sub(r'\s+', ' ', text).strip()

                # Now, split the text into words. This should be cleaner.
                # We'll rely on the split for tokenization and ensure individual tokens are not empty.
                words = [word for word in text.split(' ') if word]

                cleaned_text = ' '.join(words)
                self.textsize = len(cleaned_text)
                self._cleaned = True
                return cleaned_text

            except Exception as e:
                self.logger.error(f'Preprocessing failed: {e}', exc_info=True)
                raise

    async def process(self, input_file: str):
        self.input_string = self.preprocess(input_file)
        self.processed_file = PROCESSED_FILE
        self.postprocessed_file = POSTPROCESSED_FILE

        if not self._cleaned:
            raise RuntimeError("Must call preprocess() before process()")
            
        self.logger.debug(f'Processing to: {self.postprocessed_file}')
            
        try:
            self.logger.info(f'Loaded {len(self.input_string)} chars, {len(self.input_string.split())} words')
            self.input_array = self.input_string.split()
            self.chunk = ""
            self.output_string = ""
            self.input_word_pointer = 0
            self.output_pointer = 0

            chunkcount = 0
            if os.path.exists(SAVEDCHUNKS):
                shutil.rmtree(SAVEDCHUNKS)
            os.makedirs(SAVEDCHUNKS, exist_ok=True)

            self.loadchunk(CHUNK_SIZE)

            while True:
                if FORMATCHECK:
                    formatted_chunk = self.chunk
                else:
                    
                    chunkcount += 1
                    filename = 'chunk_' + str(chunkcount)
                    filepath = os.path.join(SAVEDCHUNKS, filename)
                    if not os.path.exists(filepath):
                        with open(filepath, 'a') as f:
                            f.write(self.chunk)
                            f.close()

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
                self.logger.warning(f'Word count mismatch! Input: {input_words}, Output: {output_words}')

            # Processed file
            with open(self.processed_file, 'w', encoding='utf-8') as f:
                f.write(self.output_string)
                self.logger.info(f'Saved {len(self.output_string)} chars to {self.processed_file}')

            # Process unformatted lines
            final_output = ''
            lines = self.output_string.split('\n')
            total_lines = len(lines)
            pointer = 0

            while pointer < total_lines:
                # Get next 10 lines (or remaining lines if less than 10)
                chunk_lines = lines[pointer:pointer+10]
                unformatted_string = '\n'.join(chunk_lines)
                formatted_string = await self.formatlines(unformatted_string)
                if final_output:  # add newline after first line
                    formatted_string = '\n' + formatted_string
                final_output += formatted_string
                pointer += 10
                self.logger.info(f'Saved {pointer} lines to {self.postprocessed_file}')
            
            # Final output
            with open(self.postprocessed_file, 'w', encoding='utf-8') as f:
                f.write(final_output)
                self.logger.info(f'Saved {len(final_output)} chars to {self.postprocessed_file}')
                
        except Exception as e:
            self.logger.error(f'Processing failed: {e}', exc_info=True)
            raise