#!/usr/bin/env python3
import logging
import asyncio
from pipeline import TextProcessingPipeline

def configure_logging():
    logging.basicConfig(
        level=logging.DEBUG,  # More verbose logging
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
            chunk_size=400,
            chunk_overlap=150
        )
        await pipeline.process_file(
            input_path="transcript.txt",
            output_path="formatted_transcript.txt"
        )
        print("Successfully created formatted_transcript.txt")
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())