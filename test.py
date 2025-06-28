import requests
import logging
from config import API_URL, API_TIMEOUT, CHUNK_SIZE, CHUNK_OVERLAP, MAX_TOKENS, STOP_SEQUENCES, REPETITION_PENALTY, TEMPERATURE, TOP_P

logger = logging.getLogger('api_test')

def test_api_connection():
    """Test the LLM API with a minimal valid request."""
    test_payload = {
        "model": "TheBloke_Mistral-7B-Instruct-v0.2-AWQ",
        "prompt": "This is a connection test. Respond with 'OK' if working.",
        "max_tokens": 5,
        "temperature": 0
    }

    try:
        logger.info(f"Testing API connection to {API_URL}")
        response = requests.post(
            API_URL,
            json=test_payload,
            timeout=API_TIMEOUT
        )
        
        response.raise_for_status()  # Raises exception for 4XX/5XX status codes
        
        data = response.json()
        if 'choices' not in data or len(data['choices']) == 0:
            logger.error("API response missing choices")
            return False
            
        logger.info(f"API Success! Response: {data}")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Connection failed: {str(e)}")
        return False
    except ValueError as e:
        logger.error(f"Invalid JSON response: {str(e)}")
        return False

def test_chunk_processing():
    """Test processing a single chunk with realistic content."""
    test_chunk = (
        "this is a test chunk of transcribed audio content containing approximately 400 "
        "characters with overlapping speech for simulation purposes the Application "
        "programming interface (api) must transform it into well-constructed paragraphs "
        "complete with appropriate punctuation and capitalization"
    )

    payload = {
        "model": "TheBloke_Mistral-7B-Instruct-v0.2-AWQ",
        "prompt": (
            "REFORMAT THIS TRANSCRIPT INTO PROFESSIONAL PROSE:\n\n"
            "Requirements:\n"
            "1. Use proper punctuation and capitalization\n"
            "2. Form coherent paragraphs\n"
            "3. Remove any filler words or repetitions\n\n"
            "Original:\n"
            f"{test_chunk}\n\n"
            "Reformatted:"
        ),
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "stop": STOP_SEQUENCES,
        "repetition_penalty": REPETITION_PENALTY,
        "top_k": 50,
        "truncate": False
    }

    try:
        logger.info("Testing chunk processing...")
        response = requests.post(
            API_URL,
            json=payload,
            timeout=API_TIMEOUT
        )
        
        response.raise_for_status()
        data = response.json()
        
        if 'choices' not in data or len(data['choices']) == 0:
            logger.error("API response missing choices")
            return False
            
        result = data['choices'][0]['text'].strip()
        if not result:
            logger.error("API returned empty content!")
            return False
            
        logger.info(f"Processed chunk successfully:\n{result}")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Chunk processing error: {str(e)}")
        return False
    except ValueError as e:
        logger.error(f"Invalid JSON response: {str(e)}")
        return False
    except KeyError as e:
        logger.error(f"Malformed API response - missing field: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting API tests...")
    if test_api_connection():
        logger.info("Proceeding to chunk processing test...")
        test_chunk_processing()