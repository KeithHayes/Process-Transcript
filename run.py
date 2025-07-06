import asyncio
import logging
from logger import configure_logging
from config import TEST_FILE
from process import ParseFile

async def main():
    configure_logging()
    logger = logging.getLogger('main')
    try:
        async with ParseFile() as parser:
            await parser.process(TEST_FILE)
        logger.info("Processing completed successfully")
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())