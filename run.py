# run.py
import asyncio
import logging
from pipeline import TextProcessingPipeline
from llm_integration import MyLLMClient  # Your LLM wrapper

def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('processing.log'),
            logging.StreamHandler()
        ]
    )

async def main():
    configure_logging()
    llm = MyLLMClient()
    
    pipeline = TextProcessingPipeline(
        llm=llm,
        chunk_size=800,  # Optimal for most LLMs
        chunk_overlap=150,
        max_retries=3
    )
    
    try:
        await pipeline.process_file(
            input_path="transcript.txt",
            output_path="formatted_transcript.txt"
        )
    except Exception as e:
        logging.error(f"Failed to process file: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    asyncio.run(main())