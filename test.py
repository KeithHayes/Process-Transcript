import asyncio
import logging
import os
import sys
import textwrap
import aiohttp
import re # Import re for post-processing demonstration

# Add parent directory to path to allow imports from config and logger
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import API_URL, TEMPERATURE, STOP_SEQUENCES, REPETITION_PENALTY, TOP_P, API_TIMEOUT
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
    
    # --- PROMPT: Complete sentences, single space separation ---
    prompt = textwrap.dedent(f"""\
        Reformat the following text into grammatically correct and complete sentences.

        Text to reformat:
        {chunktext}

        Rules for reformatting:
        1. Preserve all original words exactly.
        2. Maintain the original word order.
        3. Ensure proper capitalization for the start of each sentence.
        4. Add necessary punctuation (periods, question marks, exclamation points) to end each sentence.
        5. Single space each complete sentence using newlines.
        6. Do not add or remove any content beyond essential punctuation.

        Reformatted text:""")
    # --- END PROMPT ---

    try:
        async with session.post(
            API_URL,
            json={
                "prompt": prompt,
                "max_tokens": 500, # Keep increased max_tokens to avoid empty responses
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
                logger.debug(f"Full API response for empty text: {result}") 
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
        formatted_output_from_llm = await formatchunk(first_250_words)

        logger.info("\n--- LLM's Raw Formatted Output (single-space separated sentences) ---")
        logger.info(formatted_output_from_llm) 
        logger.info("--- End LLM's Raw Formatted Output ---\n")

        # --- POST-PROCESSING STEP: Adding newlines for display ---
        logger.info("\n--- Post-Processed Output (each sentence on new line) ---")
        # Regex to split by sentence-ending punctuation followed by a space
        # (?<=[.!?]) is a positive lookbehind assertion, ensuring the split happens AFTER the punctuation
        sentences = re.split(r'(?<=[.!?])\s+', formatted_output_from_llm)
        # Filter out any empty strings that might result from the split and strip whitespace
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Join with newlines
        post_processed_output = "\n".join(sentences)
        logger.info(post_processed_output)
        logger.info("--- End Post-Processed Output ---\n")
        # --- END POST-PROCESSING STEP ---

    except Exception as e:
        logger.error(f"An error occurred during testing: {str(e)}", exc_info=True)
    finally:
        if session:
            await session.close()
            logger.info("aiohttp session closed.")

if __name__ == "__main__":
    asyncio.run(main())