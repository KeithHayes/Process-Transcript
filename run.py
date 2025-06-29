import asyncio
import logging
from logger import configure_logging
from pipeline import TextProcessingPipeline
from config import CHUNK_SIZE, CHUNK_OVERLAP, INPUT_FILE, PROCESSED_FILE
from process import ParseFile

def prepare_data():
    configure_logging()
    filerunner = ParseFile()
    filerunner.preprocess(INPUT_FILE)
    filerunner.process(PROCESSED_FILE)

async def main():
    configure_logging()
    logger = logging.getLogger('main')
    try:
        prepare_data()
        #logger.info("Starting transcript processing pipeline")
        #pipeline = TextProcessingPipeline(
        #    chunk_size=CHUNK_SIZE,
        #    chunk_overlap=CHUNK_OVERLAP
        #)
        #await pipeline.process_file()
        logger.info("Processing completed")
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())