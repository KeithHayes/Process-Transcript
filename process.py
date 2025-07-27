import os
import re
import logging
from logger import configure_logging
import textwrap
import aiohttp
import asyncio
from config import (
    API_URL, API_TIMEOUT, MAX_TOKENS, STOP_SEQUENCES, TEST_MODE,
    REPETITION_PENALTY, TEMPERATURE, TOP_P, TOP_T, SENTENCE_MARKER,
    CHUNK_OVERLAP, OUTPUT_CHUNK_SIZE, TEST_INPUT, TEST_OUTPUT,
    PROCESSED_FILE, POSTPROCESSED_FILE, TEST_FILE
)

class ParseFile:
    def __init__(self):
        self.input_string = ""
        self.chunk = ""
        self.output_string = ""
        self._cleaned = False
        self.api_url = API_URL
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.input_array = []

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def loadchunk(self, word_count):
        words_loaded = 0
        words = []
        while words_loaded < word_count and self.input_word_pointer < len(self.input_array):
            words.append(self.input_array[self.input_word_pointer])
            self.input_word_pointer += 1
            words_loaded += 1

        wordschunk = ' '.join(words)
        self.chunk = (self.chunk + ' ' + wordschunk).strip()  # Ensure space between chunks
        self.logger.info(f'Loaded {words_loaded} words (input pointer: {self.input_word_pointer})')
        return self.chunk
    
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
        protected = formatted_output.replace('\n', SENTENCE_MARKER)
        output = protected.lower()
        output = re.sub(f'[^a-z\\s{re.escape(SENTENCE_MARKER)}]', '', output)
        return output.replace(SENTENCE_MARKER, '\n')

    def preprocess(self, input_file):
        self.input_file = input_file
        self.logger.debug(f'Preprocessing: {self.input_file}')
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                text = f.read()

            if TEST_MODE == "desiredoutput":
                self.input_string = text
                self.input_array = text.split()
                self.textsize = len(text)
                return text

            text = text.lower()
            text = text.replace("'", "'").replace('"', '"')
            text = text.replace("—", " -- ")
            text = re.sub(r"[^a-z0-9'\-\s]", " ", text)
            text = re.sub(r'\s+', ' ', text).strip()

            words = [word for word in text.split(' ') if word]
            cleaned_text = ' '.join(words)
            self.input_string = cleaned_text
            self.input_array = words
            self.textsize = len(cleaned_text)
            return cleaned_text

        except Exception as e:
            self.logger.error(f'Preprocessing failed: {e}', exc_info=True)
            raise

    def getdesiredchunk(self, text):
        try:
            # Preserve trailing whitespace but remove leading whitespace
            stripped_text = text.lstrip()
            trailing_whitespace = text[len(stripped_text.rstrip()):] if text.rstrip() != text else ''
            
            target_words = stripped_text.split()
            num_words = len(target_words)

            input_words = self.deformat(self.input_string).strip().split()
            for i in range(len(input_words) - num_words + 1):
                if input_words[i:i + num_words] == target_words:
                    start_word_index = i
                    break
            else:
                raise ValueError("Chunk not found in input_string.")

            with open(os.path.join("files", "desired_output.txt"), "r", encoding='utf-8') as f:
                lines = [line.rstrip('\n') for line in f.readlines()]

            word_locations = []
            for line_index, line in enumerate(lines):
                words_in_line = line.strip().split()
                for word_index, word in enumerate(words_in_line):
                    word_locations.append((line_index, word_index))

            if start_word_index + num_words > len(word_locations):
                raise ValueError("Chunk exceeds length of desired output.")

            chunk_locations = word_locations[start_word_index:start_word_index + num_words]
            line_buffer = {}
            for line_index, word_index in chunk_locations:
                original_line = lines[line_index]
                words_in_line = original_line.strip().split()
                word = words_in_line[word_index]
                
                if line_index not in line_buffer:
                    line_buffer[line_index] = {'words': []}
                line_buffer[line_index]['words'].append(word)

            # Reconstruct lines without leading whitespace
            ordered_lines = []
            for line_index in sorted(line_buffer):
                line_data = line_buffer[line_index]
                reconstructed_line = ' '.join(line_data['words'])
                ordered_lines.append(reconstructed_line)

            desired_chunk = '\n'.join(ordered_lines) + trailing_whitespace
            
            return desired_chunk

        except Exception as e:
            self.logger.error(f'getdesiredchunk failed: {e}', exc_info=True)
            return text

    async def format(self, text):
        formatted = ""
        chunk = self.deformat(text)
        match TEST_MODE:
            case "unformatted":
                formatted = chunk
            case "desiredoutput":
                formatted = self.getdesiredchunk(chunk)
            case "run":
                formatted = await self.formatchunk(chunk)
            case _:
                formatted = chunk
        return formatted
    
    def find_first_mismatch(self, str1, str2):
        min_len = min(len(str1), len(str2))
        for i in range(min_len):
            if str1[i] != str2[i]:
                return f"Mismatch at index {i}: '{str1[i]}' != '{str2[i]}'"
        if len(str1) != len(str2):
            return f"Mismatch at index {min_len}: One string is longer"
        return "Strings are identical"

    def split_into_two_chunks(self, text, n):
        """Improved version that preserves word boundaries and spacing"""
        if not text.strip():
            return "", ""
            
        words = re.findall(r'\S+\s*', text)  # Preserve original spacing
        if n >= len(words):
            return text, ""
            
        first_part = ''.join(words[:n])
        second_part = ''.join(words[n:])
        
        # Ensure proper spacing between chunks
        if not first_part.endswith((' ', '\n')) and not second_part.startswith((' ', '\n')):
            first_part += ' '
            
        return first_part.rstrip(), second_part

    async def process(self, input_file: str):
        self.input_string = self.preprocess(input_file)
        self.cleanedinput_file = PROCESSED_FILE
        self.output_file = POSTPROCESSED_FILE
            
        try:
            input_string = self.input_string
            output_string = ""
            context_window = ""
            chunk_size = OUTPUT_CHUNK_SIZE
            overlap_size = CHUNK_OVERLAP
            total_chunk_size = chunk_size + overlap_size
                
            first_chunk, remaining_input = self.split_into_two_chunks(input_string, total_chunk_size)
            context_window = await self.format(first_chunk)
                
            while remaining_input.strip():
                output_part, overlap_part = self.split_into_two_chunks(context_window, chunk_size)
                
                # Ensure proper spacing when combining
                if output_string and not output_string.endswith((' ', '\n')):
                    output_string += ' '
                output_string += output_part
                
                next_chunk, remaining_input = self.split_into_two_chunks(
                    remaining_input, 
                    chunk_size - overlap_size
                )
                
                if not next_chunk.strip() and not remaining_input.strip():
                    break
                
                # Combine with proper spacing
                combined = overlap_part
                if combined and next_chunk:
                    if not combined.endswith((' ', '\n')) and not next_chunk.startswith((' ', '\n')):
                        combined += ' '
                combined += next_chunk
                
                context_window = await self.format(combined)

            # Add final chunk with proper spacing
            if output_string and not output_string.endswith((' ', '\n')):
                output_string += ' '
            output_string += context_window

            
            with open(TEST_INPUT, "w", encoding='utf-8') as f:
                f.write(self.input_string)

            with open(TEST_OUTPUT, "w", encoding='utf-8') as f:
                f.write(output_string.strip())

            if TEST_MODE == "desiredoutput":
                with open(os.path.join("files", "desired_output.txt"), "r", encoding='utf-8') as f:
                    desiredcontent = f.read()
                result = self.find_first_mismatch(desiredcontent, output_string)
                print(result)

            return output_string.strip()

        except Exception as e:
            self.logger.error(f'Processing failed: {e}', exc_info=True)
            raise

async def main():
    configure_logging()
    logger = logging.getLogger('main')
    try:
        async with ParseFile() as parser:
            await parser.process(TEST_FILE)
        logger.info("Processing completed successfully")
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())