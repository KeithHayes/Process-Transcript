import asyncio
import logging
import os
import sys
import textwrap
import aiohttp

# Add parent directory to path to allow imports from config and logger
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import API_URL, MAX_TOKENS, TEMPERATURE, STOP_SEQUENCES, REPETITION_PENALTY, TOP_P, API_TIMEOUT
from logger import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

session = None

async def formatchunk(chunktext: str) -> str:
    global session
    if session is None:
        logger.warning("aiohttp session not initialized. Creating a temporary one.")
        session = aiohttp.ClientSession()

    chunklength = len(chunktext)
    logger.debug(f'Formatting chunk of {chunklength} chars')
    
    # --- UPDATED PROMPT FOR BETTER SENTENCE SEPARATION ---
    prompt = textwrap.dedent(f"""\
        Reformat the following text. Each complete sentence must be on its own separate line.

        Text to reformat:
        {chunktext}

        Rules for reformatting:
        1. Preserve all original words exactly.
        2. Maintain the original word order.
        3. Do not add or remove any content (words, numbers, symbols) beyond essential punctuation and newlines.
        4. Every complete sentence MUST end with appropriate punctuation (. ! ?) and be immediately followed by a single newline character.
        5. DO NOT include any blank lines between sentences. Each sentence should start on the line directly following the previous one.
        6. Ensure capitalization is correct for the start of each sentence.

        Reformatted text:""")
    # --- END UPDATED PROMPT ---

    try:
        async with session.post(
            API_URL,
            json={
                "prompt": prompt,
                "max_tokens": MAX_TOKENS,
                "temperature": TEMPERATURE,
                "stop": STOP_SEQUENCES,
                "repetition_penalty": REPETITION_PENALTY,
                "top_p": TOP_P
            },
            timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
        ) as response:
            if response.status != 200:
                error = await response.text()
                logger.warning(f"API error {response.status}: {error}")
                return chunktext
            
            result = await response.json()
            # It's crucial here that the LLM's output is directly used or minimally stripped.
            # .strip() could remove the final newline if the LLM correctly adds it,
            # but usually, LLMs produce some trailing whitespace which .strip() handles well.
            formatted_text = result.get("choices", [{}])[0].get("text", "").strip()
            
            if not formatted_text:
                logger.warning("Received empty response from API")
                return chunktext
            
            return formatted_text
            
    except asyncio.TimeoutError:
        logger.warning("API request timed out")
        return chunktext
    except Exception as e:
        logger.error(f"API call failed: {str(e)}")
        return chunktext

async def main():
    global session
    session = aiohttp.ClientSession()

    try:
        preprocessed_file_path = 'files/transcript_preprocessed.txt' 
        first_250_words = ""
        try:
            with open(preprocessed_file_path, 'r', encoding='utf-8') as f:
                full_text = f.read()
                words = full_text.split()
                first_250_words = ' '.join(words[:250])
            logger.info(f"Loaded first 250 words from '{preprocessed_file_path}'.")
            logger.debug(f"Input text for formatchunk: '{first_250_words[:100]}...'")

        except FileNotFoundError:
            logger.error(f"Error: '{preprocessed_file_path}' not found. Please ensure it's in the correct directory.")
            return
        except Exception as e:
            logger.error(f"Error reading '{preprocessed_file_path}': {e}")
            return

        logger.info("Calling formatchunk with the extracted text...")
        formatted_output = await formatchunk(first_250_words)

        logger.info("\n--- Formatted Output ---")
        logger.info(formatted_output) 
        logger.info("--- End Formatted Output ---\n")

    except Exception as e:
        logger.error(f"An error occurred during testing: {str(e)}", exc_info=True)
    finally:
        if session:
            await session.close()
            logger.info("aiohttp session closed.")

if __name__ == "__main__":
    asyncio.run(main())