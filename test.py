import asyncio
import logging
import os
import sys
import textwrap
import aiohttp
from unittest.mock import AsyncMock, patch

# Add parent directory to path to allow imports from config and logger
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import API_URL, MAX_TOKENS, TEMPERATURE, STOP_SEQUENCES, REPETITION_PENALTY, TOP_P, API_TIMEOUT
from logger import configure_logging

# Configure logging for the test file
configure_logging()
logger = logging.getLogger(__name__)

# Global session variable for aiohttp (mimicking ParseFile's session handling)
# In a real test/dev scenario, you might pass this around or use a fixture.
session = None

async def formatchunk(chunktext: str) -> str:
    """
    Reformats a given chunk of text using an external LLM API.
    This function is copied here from process.py for isolated debugging.
    """
    global session
    if session is None:
        logger.warning("aiohttp session not initialized. Creating a temporary one.")
        session = aiohttp.ClientSession() # This will be closed in the main function

    chunklength = len(chunktext)
    logger.debug(f'Formatting chunk of {chunklength} chars')
    prompt = textwrap.dedent(f"""\
        Reformatted this text with proper sentence formatting:

        {chunktext}

        Rules:
        1. Preserve all original words exactly
        4. Maintain original word order
        5. Do not add any new content
        4. Identify all unformatted sentences.
        6. Format all unformatted sentences and add a line break before and after each complete sentence.

        Reformatted text:""")

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
    """
    Main function to orchestrate the formatchunk debugging.
    Reads the first 250 words from transcript_preprocessed.txt
    and passes them to the formatchunk function.
    """
    global session
    session = aiohttp.ClientSession() # Initialize the session for formatchunk

    try:
        # Read the first 250 words from transcript_preprocessed.txt
        preprocessed_file_path = 'files/transcript_preprocessed.txt' # Assuming it's in the same directory
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

        # Call the formatchunk function with the loaded text
        logger.info("Calling formatchunk with the extracted text...")
        formatted_output = await formatchunk(first_250_words)

        logger.info("\n--- Formatted Output ---")
        logger.info(formatted_output)
        logger.info("--- End Formatted Output ---\n")

        # You can add more assertions or print statements here for debugging
        # For example, save the output to a file or compare it against a known good output.

    except Exception as e:
        logger.error(f"An error occurred during testing: {str(e)}", exc_info=True)
    finally:
        if session:
            await session.close() # Close the session when done
            logger.info("aiohttp session closed.")

if __name__ == "__main__":
    asyncio.run(main())