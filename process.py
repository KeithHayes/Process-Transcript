import os
import re
import logging
import textwrap
import aiohttp
import hashlib
from config import (API_URL, API_TIMEOUT, MAX_TOKENS, STOP_SEQUENCES, TEST_MODE,
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
    
    async def formatchunk1(self, chunktext: str) -> str:
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

                text = text.lower()
                text = text.replace("’", "'").replace("“", '"').replace("”", '"')
                text = text.replace("—", " -- ") # Normalize em-dashes to spaces
                text = re.sub(r"[^A-Za-z0-9'\-]+", " ", text)
                text = re.sub(r'\s+', ' ', text).strip()

                words = [word for word in text.split(' ') if word]
                cleaned_text = ' '.join(words)
                self.textsize = len(cleaned_text)
                self._cleaned = True
                return cleaned_text

            except Exception as e:
                self.logger.error(f'Preprocessing failed: {e}', exc_info=True)
                raise

    # the entry point

    def checksum_md5(text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    async def format(self, text):
        TEST_MODE = 'unfiltered'
        match TEST_MODE:
            case "unfiltered":
                return text
            case "desired":
                print("Running in desired mode.")
                checksum = checksum_md5(text)

                return text
            case "run":
                formatted_chunk = await self.formatchunk1(text)
                return text
            case _:
                return text
    
    def find_first_mismatch(self, str1, str2):
        min_len = min(len(str1), len(str2))
        for i in range(min_len):
            if str1[i] != str2[i]:
                return f"Mismatch at index {i}: '{str1[i]}' != '{str2[i]}'"
        if len(str1) != len(str2):
            return f"Mismatch at index {min_len}: One string is longer"
        return "Strings are identical"

    

    def split_into_two_chunks(self, text, n):
        words = text.split()
        first_chunk = ' '.join(words[:n]) if words else ""
        second_chunk = ' '.join(words[n:]) if words else ""
        return first_chunk, second_chunk


    async def process(self, input_file: str):
        self.input_string = self.preprocess(input_file)
        # file paths defined
        self.cleanedinput_file = PROCESSED_FILE
        self.output_file = POSTPROCESSED_FILE

        if not self._cleaned:
            raise RuntimeError("Must call preprocess() before process()")
            
        self.logger.debug(f'Processing to: {self.output_file}')
            
        try:

            input_string = self.input_string
            output_string = ""
            context_window = ""
            chunk_size = OUTPUT_CHUNK_SIZE
            overlap_size = CHUNK_OVERLAP
            total_chunk_size = chunk_size + overlap_size
            first_chunk, remaining_input = self.split_into_two_chunks(input_string, total_chunk_size)
            context_window = await self.format(first_chunk)
            while remaining_input:
                output_part, overlap_part = self.split_into_two_chunks(context_window, chunk_size)
                output_string += output_part + " "
                next_chunk, remaining_input = self.split_into_two_chunks(remaining_input, chunk_size)
                context_window = overlap_part + " " + next_chunk
                context_window = await self.format(context_window)

            output_string += context_window
            


            with open(os.path.join("files", "testinput.txt"), "w") as f:
                f.write(self.input_string)
            with open(os.path.join("files", "testoutput.txt"), "w") as f:
                f.write(output_string)

            result = self.find_first_mismatch(self.input_string, output_string)
            
            print(result)  # Output: Mismatch at index 3: 'd' != 'x'


                
        except Exception as e:
            self.logger.error(f'Processing failed: {e}', exc_info=True)
            raise