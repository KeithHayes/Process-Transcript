# Core processing parameters
CHUNK_SIZE = 1000  # Optimal for most transcripts
CHUNK_OVERLAP = 200  # Enough for smooth transitions
MIN_SENTENCE_LENGTH = 3  # Minimum words to consider complete
MAX_FRAGMENT_LENGTH = 100  # Max chars for incomplete fragments

# API configuration
API_URL = "http://0.0.0.0:5000/v1/completions"
API_TIMEOUT = 60  # seconds
MAX_TOKENS = 150
STOP_SEQUENCES = ["\n\n", "###", "##"]

# Formatting rules
SPEAKER_FORMAT = "{name}: {content}"  # Consistent speaker format
REPETITION_PENALTY = 1.2
TEMPERATURE = 0.7
TOP_P = 0.9

# Validation parameters
MAX_SENTENCE_VALIDATION_ERRORS = 5

__all__ = [
    'CHUNK_SIZE', 'CHUNK_OVERLAP', 'API_URL', 'API_TIMEOUT',
    'MAX_TOKENS', 'STOP_SEQUENCES', 'REPETITION_PENALTY',
    'TEMPERATURE', 'TOP_P', 'MIN_SENTENCE_LENGTH',
    'MAX_FRAGMENT_LENGTH', 'SPEAKER_FORMAT',
    'MAX_SENTENCE_VALIDATION_ERRORS'
]