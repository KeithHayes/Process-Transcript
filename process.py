import re
import logging
import textwrap
import aiohttp
from config import (
    CLEANED_FILE, API_URL, API_TIMEOUT, MAX_TOKENS, STOP_SEQUENCES,
    REPETITION_PENALTY, TEMPERATURE, TOP_P, TOP_T, SENTENCE_MARKER,
    CHUNK_SIZE, CHUNK_OVERLAP, OUTPUT_CHUNK_SIZE, FORMATCHECK,
    PROCESSED_FILE, POSTPROCESSED_FILE, LINECHECK, MAX_SENTENCE_LENGTH,
    STRICT_PUNCTUATION_RULES, PRESERVE_CASE
)

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
        self.original_words = []

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def count_words(self, text):
        return len(text.split()) if text.strip() else 0

    def validate_word_preservation(self, original, processed):
        """Ensure no words were changed during processing"""
        original_words = original.split()
        processed_words = processed.split()
        
        if len(original_words) != len(processed_words):
            self.logger.error(f"Word count mismatch: original {len(original_words)} vs processed {len(processed_words)}")
            return False
            
        for ow, pw in zip(original_words, processed_words):
            if ow.lower() != pw.lower():
                self.logger.error(f"Word altered: '{ow}' -> '{pw}'")
                return False
        return True

    def deformat(self, formatted_output):
        """Convert formatted text back to plain words while preserving sentence boundaries"""
        # Replace sentence markers with newlines
        protected = formatted_output.replace('\n', SENTENCE_MARKER)
        
        if PRESERVE_CASE:
            # Only remove punctuation if preserving case
            output = re.sub(f'[^a-zA-Z\\s{re.escape(SENTENCE_MARKER)}]', '', protected)
        else:
            # Lowercase and remove punctuation
            output = protected.lower()
            output = re.sub(f'[^a-z\\s{re.escape(SENTENCE_MARKER)}]', '', output)
            
        return output.replace(SENTENCE_MARKER, '\n')

    def loadchunk(self, word_count):
        words_loaded = 0
        words = []
        while words_loaded < word_count and self.input_word_pointer < len(self.input_array):
            word = self.input_array[self.input_word_pointer]
            words.append(word)
            self.original_words.append(word)
            self.input_word_pointer += 1
            words_loaded += 1

        wordschunk = ' '.join(words)
        self.chunk = (self.chunk + ' ' + wordschunk).strip()
        self.logger.info(f'Loaded {words_loaded} words (input pointer: {self.input_word_pointer})')
        return self.chunk
    
    def savechunk(self):
        try:
            if not self.chunk:
                return
                
            chunkwords = [w for w in self.chunk.split(' ') if w]
            is_final_chunk = self.input_word_pointer >= len(self.input_array)
            
            if is_final_chunk:
                save_words = chunkwords
                self.logger.debug(f'Final chunk detected - saving all {len(save_words)} words')
                save_words_string = ' '.join(save_words)
                self.output_string += save_words_string
                self.output_pointer += len(save_words_string)
                self.chunk = ''
            else:
                save_words = chunkwords[:OUTPUT_CHUNK_SIZE]
                if save_words:
                    save_words_string = ' '.join(save_words) + ' '
                    self.output_string += save_words_string
                    self.output_pointer += len(save_words_string)
                remaining_words = chunkwords[OUTPUT_CHUNK_SIZE:]
                self.chunk = ' '.join(remaining_words)
        except Exception as e:
            self.logger.error(f'Save of chunk failed: {e}', exc_info=True)
            raise

    async def formatchunk(self, chunktext: str) -> str:
        if self.session is None:
            self.session = aiohttp.ClientSession()
        
        prompt = textwrap.dedent(f"""\
            MUST maintain the EXACT original words and their order.
            MUST preserve all original words exactly as they appear.
            MUST NOT modify, add, or delete any words.
            Put each complete sentence on its own line.
            Only combine words into sentences when they clearly form a complete thought.
            Keep fragments on their own line if they don't form complete sentences.
            Add proper punctuation to complete sentences.
            Capitalize first word of each complete sentence.
            Preserve all original capitalization if it's significant.
            Never split words or hyphenated phrases.
            Important abbreviations: {STRICT_PUNCTUATION_RULES['abbreviations']}

            Input: {chunktext}

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
                
                if not self.validate_word_preservation(chunktext, formatted):
                    self.logger.warning("Word preservation validation failed, using original chunk")
                    return chunktext
                    
                return formatted if formatted else chunktext
        except Exception as e:
            self.logger.error(f"Error formatting chunk: {str(e)}")
            return chunktext

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
                    Add proper punctuation to complete sentences.
                    Capitalize first word only if it starts a complete sentence.
                    Preserve original capitalization for proper nouns and special cases.
                    Keep fragments as-is if they don't form complete sentences.
                    Important abbreviations: {STRICT_PUNCTUATION_RULES['abbreviations']}

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
                        formatted_lines.append(line)
                        continue
                    
                    result = await response.json()
                    formatted_line = result.get("choices", [{}])[0].get("text", "").strip()
                    
                    if not formatted_line:
                        self.logger.warning(f"Empty response for line: {line}")
                        formatted_lines.append(line)
                    else:
                        if not self.validate_word_preservation(line, formatted_line):
                            self.logger.warning(f"Word preservation failed for line, using original: {line}")
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
                # Protect hyphenated words and apostrophes
                text = re.sub(r'(\w-\w)', lambda m: m.group(1).replace('-', 'HYPHEN'), text)
                text = re.sub(r"(\w'\w)", lambda m: m.group(1).replace("'", "APOSTROPHE"), text)
                
                # Standardize whitespace
                text = re.sub(r'\s+', ' ', text).strip()
                
                # Clean while preserving special characters in words
                cleaned_chars = []
                for i, char in enumerate(text):
                    if char.isalnum() or char.isspace():
                        cleaned_chars.append(char)
                    elif (i > 0 and i < len(text) - 1 and
                          text[i-1].isalpha() and text[i+1].isalpha()):
                        cleaned_chars.append(char)

                text = ''.join(cleaned_chars)
                # Restore protected characters
                text = text.replace('HYPHEN', '-').replace('APOSTROPHE', "'")
                self.textsize = len(text)
                self._cleaned = True
                return text
        except Exception as e:
            self.logger.error(f'Preprocessing failed: {e}', exc_info=True)
            raise

    async def process(self, input_file: str):
        self.input_string = self.preprocess(input_file)
        self.processed_file = PROCESSED_FILE
        self.postprocessed_file = POSTPROCESSED_FILE

        if not self._cleaned:
            raise RuntimeError("Must call preprocess() before process()")
            
        try:
            self.logger.info(f'Loaded {len(self.input_string.split())} words')
            self.input_array = self.input_string.split()
            self.chunk = ""
            self.output_string = ""
            self.input_word_pointer = 0
            self.output_pointer = 0
            self.original_words = []
            
            # First pass - chunk processing
            self.loadchunk(CHUNK_SIZE)

            while True:
                if FORMATCHECK:
                    formatted_chunk = self.chunk
                else:
                    formatted_chunk = await self.formatchunk(self.chunk)
                    # Mark sentence boundaries while preserving words
                    sentence_ends_marked = re.sub(
                        r'(?<=[.?!])\s+', 
                        SENTENCE_MARKER, 
                        formatted_chunk
                    )
                    sentence_starts_marked = re.sub(
                        r'\s+(?=[A-Z][a-z])', 
                        SENTENCE_MARKER, 
                        sentence_ends_marked
                    )
                    self.chunk = self.deformat(sentence_starts_marked)
                
                self.savechunk()
                
                if self.input_word_pointer >= len(self.input_array) and not self.chunk.strip():
                    break
                    
                if self.input_word_pointer < len(self.input_array):
                    self.loadchunk(CHUNK_SIZE - CHUNK_OVERLAP)

            # Second pass - line formatting
            final_output = ''
            lines = self.output_string.split('\n')
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
            
            # Final validation
            original_word_count = len(self.original_words)
            processed_word_count = len(final_output.split())
            if original_word_count != processed_word_count:
                self.logger.error(f"Final word count mismatch: original {original_word_count} vs processed {processed_word_count}")
            
            # Save final output
            with open(self.postprocessed_file, 'w', encoding='utf-8') as f:
                f.write(final_output)
                
        except Exception as e:
            self.logger.error(f'Processing failed: {e}', exc_info=True)
            raise