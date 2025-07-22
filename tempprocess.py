import os
import re
import logging
import textwrap
import aiohttp
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

    def getdesiredchunk(self, text):
        """
        Given a chunk from self.input_string (which has no punctuation),
        find its word index in self.input_string,
        then extract a chunk of the same word length starting at that index from files/desired_output.txt,
        preserving original line breaks.
        """
        try:
            # Tokenize by space
            target_words = text.strip().split()
            num_words = len(target_words)

            # Tokenize self.input_string
            input_words = self.input_string.strip().split()
            for i in range(len(input_words) - num_words + 1):
                if input_words[i:i + num_words] == target_words:
                    start_word_index = i
                    break
            else:
                raise ValueError("Chunk not found in input_string.")

            # Load desired_output with original line breaks
            with open(os.path.join("files", "desired_output.txt"), "r", encoding='utf-8') as f:
                lines = f.readlines()

            # Flatten words across lines while keeping mapping: word index → (line index, word index in line)
            word_locations = []
            for line_index, line in enumerate(lines):
                words_in_line = line.strip().split()
                for word_index, word in enumerate(words_in_line):
                    word_locations.append((line_index, word_index))

            if start_word_index + num_words > len(word_locations):
                raise ValueError("Chunk exceeds length of desired output.")

            # Collect the chunk words with their line positions
            chunk_locations = word_locations[start_word_index:start_word_index + num_words]

            # Reconstruct the chunk with preserved line breaks
            line_buffer = {}
            for line_index, word_index in chunk_locations:
                line = lines[line_index].strip().split()
                word = line[word_index]
                line_buffer.setdefault(line_index, []).append(word)

            # Combine the chunk lines in order
            ordered_lines = [line_buffer[i] for i in sorted(line_buffer)]
            desired_chunk = '\n'.join(' '.join(words) for words in ordered_lines)

            return desired_chunk

        except Exception as e:
            self.logger.error(f'getdesiredchunk failed: {e}', exc_info=True)
            return text  # fallback


        

    async def format(self, text):
        TEST_MODE = 'builddataset'
        match TEST_MODE:
            case "noformat":
                return text
            case "builddataset":
                print("Generates training data.")
                newtext = self.getdesiredchunk(text)


                return newtext
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
    self.cleanedinput_file = PROCESSED_FILE
    self.output_file = POSTPROCESSED_FILE

    if not self._cleaned:
        raise RuntimeError("Must call preprocess() before process()")
        
    self.logger.debug(f'Processing to: {self.output_file}')
    
    try:
        input_words = self.input_string.split()
        chunk_size = OUTPUT_CHUNK_SIZE
        overlap_size = CHUNK_OVERLAP
        
        formatted_chunks = []
        input_pointer = 0
        total_words = len(input_words)

        while input_pointer < total_words:
            end_pointer = min(input_pointer + chunk_size + overlap_size, total_words)
            chunk_words = input_words[input_pointer:end_pointer]
            chunk_text = ' '.join(chunk_words)
            
            formatted = await self.format(chunk_text)
            formatted_chunks.append(formatted)
            
            input_pointer += chunk_size  # move by chunk_size only

        # Step 2: Merge chunks by removing overlaps (string based)
        # We'll keep the first chunk whole,
        # then for each subsequent chunk, remove any prefix that matches a suffix of the previous output.

        def remove_overlap(prev: str, curr: str) -> str:
            # Try to find the longest overlap where prev's suffix matches curr's prefix
            max_overlap_len = min(len(prev), len(curr))
            for olap_len in range(max_overlap_len, 0, -1):
                if prev.endswith(curr[:olap_len]):
                    return curr[olap_len:]
            return curr  # no overlap

        merged_text = formatted_chunks[0]
        for chunk in formatted_chunks[1:]:
            chunk_no_overlap = remove_overlap(merged_text, chunk)
            # Join with two newlines to preserve paragraph breaks clearly
            merged_text += "\n\n" + chunk_no_overlap.strip()

        # Step 3: Save input and output for debugging
        with open(os.path.join("files", "testinput.txt"), "w", encoding='utf-8') as f:
            f.write(self.input_string)
        with open(os.path.join("files", "testoutput.txt"), "w", encoding='utf-8') as f:
            f.write(merged_text)

        # Step 4: Optionally check differences (you already have this)
        result = self.find_first_mismatch(self.input_string, merged_text)
        print(result)

    except Exception as e:
        self.logger.error(f'Processing failed: {e}', exc_info=True)
        raise
