# run.py
import asyncio
import logging
from pipeline import TextProcessingPipeline
from llm_integration import MyLLMClient

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
        llm = MyLLMClient(api_url="http://0.0.0.0:5000/v1/completions")
        
        pipeline = TextProcessingPipeline(
            llm=llm,
            chunk_size=800,  # Optimal size for most LLMs
            chunk_overlap=200,  # Enough for context
            max_retries=3
        )
        
        await pipeline.process_file(
            input_path="transcript.txt",
            output_path="formatted_transcript.txt"
        )
        
        print("Successfully processed transcript with proper formatting!")
        
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    asyncio.run(main())