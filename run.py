#!/usr/bin/env python3
import logging
import asyncio
from pipeline import TextProcessingPipeline

def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('transcript_processor.log'),
            logging.StreamHandler()
        ]
    )

async def main():
    configure_logging()
    
    try:
        pipeline = TextProcessingPipeline(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                await pipeline.process_file(
                    input_path="transcript.txt",
                    output_path="formatted_transcript.txt"
                )
                print("Successfully created formatted_transcript.txt")
                break
            except Exception as e:
                if attempt == max_attempts - 1:
                    logging.error(f"Failed after {max_attempts} attempts: {str(e)}")
                    raise
                wait_time = 2 ** attempt
                logging.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())