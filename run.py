#!/usr/bin/env python3
import logging
import asyncio
from pipeline import TextProcessingPipeline

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    pipeline = TextProcessingPipeline(
        chunk_size=1200,
        chunk_overlap=200
    )
    
    try:
        await pipeline.process_file(
            input_path="transcript.txt",
            output_path="formatted.txt"
        )
        print("Successfully created formatted.txt")
    except Exception as e:
        logging.error(f"Failed to process file: {e}")

if __name__ == "__main__":
    asyncio.run(main())