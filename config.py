# __init__.py
CHUNK_SIZE = 400  # Optimal for most transcripts
CHUNK_OVERLAP = 150  # Enough for smooth transitions
API_URL = "http://0.0.0.0:5000/v1/completions"
API_TIMEOUT = 30  # seconds

__all__ = ['CHUNK_SIZE', 'CHUNK_OVERLAP', 'API_URL', 'API_TIMEOUT']

if __name__ == "__main__":
    print(f"Config loaded: {CHUNK_SIZE=}, {CHUNK_OVERLAP=}")