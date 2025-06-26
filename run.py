import logging
import asyncio
from pipeline import TextProcessingPipeline
from config import CHUNK_SIZE, CHUNK_OVERLAP

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
    pipeline = TextProcessingPipeline(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    await pipeline.process_file(
        input_path="transcript.txt",
        output_path="formatted_transcript.txt"
    )

if __name__ == "__main__":
    asyncio.run(main())