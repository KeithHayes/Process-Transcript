# config.py
CHUNK_SIZE = 1200  # Optimal for most transcripts
CHUNK_OVERLAP = 200  # Enough for smooth transitions
API_URL = "http://0.0.0.0:5000/v1/completions"
API_TIMEOUT = 60  # seconds
MAX_TOKENS = 150  # Prevent excessive generation
STOP_SEQUENCES = ["\n\n", "###", "##"]  # Paragraph/heading breaks
REPETITION_PENALTY = 1.2  # Critical for Mistral models
TEMPERATURE = 0.7  # Reduce repetition
TOP_P = 0.9

__all__ = ['CHUNK_SIZE', 'CHUNK_OVERLAP', 'API_URL', 'API_TIMEOUT', 'MAX_TOKENS', 'STOP_SEQUENCES',
           'REPETITION_PENALTY', 'TEMPERATURE', 'TOP_P']

if __name__ == "__main__":
    print(f"Config loaded: {CHUNK_SIZE=}, {CHUNK_OVERLAP=}")
