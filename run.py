import asyncio
import logging
from logger import configure_logging
from pipeline import TextProcessingPipeline
from config import CHUNK_SIZE, CHUNK_OVERLAP, INPUT_FILE, PROCESSED_FILE
from process import ParseFile

async def prepare_data():
    configure_logging()
    async with ParseFile() as filerunner:
        filerunner.preprocess(INPUT_FILE)
        await filerunner.process(PROCESSED_FILE)

async def main():
    configure_logging()
    logger = logging.getLogger('main')
    try:
        await prepare_data()
        logger.info("Processing completed successfully")
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())