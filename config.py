# Chunk processing configuration
CHUNK_SIZE = 250                 # Initial chunk size in words
CHUNK_OVERLAP = 100              # Words to carry over between chunks
OUTPUT_CHUNK_SIZE = 150          # Words to output from each processed chunk

# Text processing parameters
MIN_SENTENCE_LENGTH = 5          # Minimum words to consider a complete sentence
MAX_FRAGMENT_LENGTH = 50         # Maximum allowed fragment length before forcing sentence break
SENTENCE_MARKER = chr(0x0a)      # Unicode character to mark sentence boundaries

# File paths
INPUT_FILE = 'files/transcript.txt'
CLEANED_FILE = 'files/transcript_preprocessed.txt'
PROCESSED_FILE = 'files/transcript_processed.txt'
OUTPUT_FILE = 'files/transcript_formatted.txt'

# API configuration
API_URL = "http://0.0.0.0:5000/v1/completions"
API_TIMEOUT = 90                 # Increased timeout for better reliability
MAX_TOKENS = 500                 # Increased token limit for better formatting
STOP_SEQUENCES = ["\n\n", "###", "##", "</end>"]

# Formatting templates
SPEAKER_FORMAT = "{name}: {content}"

# Language model parameters
REPETITION_PENALTY = 1.15        # Slightly reduced to allow necessary repetition
TEMPERATURE = 0.05               # Lower temperature for more consistent formatting
TOP_P = 0.9                      # Higher top_p for better creativity in punctuation
TOP_K = 50                       # Added top_k sampling for better diversity
TOP_T = TOP_K

# Validation and logging
MAX_SENTENCE_VALIDATION_ERRORS = 3  # Stricter validation
LOG_DIR = 'logs'
LOG_FILE = 'runlog.log'
DEBUG_LOG_FILE = 'debug.log'

# Special processing flags
PRESERVE_CASE = True             # Preserve original capitalization where appropriate
STRICT_PUNCTUATION = True        # Enforce strict punctuation rules

# Debug flags
LOOPCHECK = False


__all__ = [
    'CHUNK_SIZE', 'CHUNK_OVERLAP', 'OUTPUT_CHUNK_SIZE',
    'MIN_SENTENCE_LENGTH', 'MAX_FRAGMENT_LENGTH', 'SENTENCE_MARKER',
    'INPUT_FILE', 'CLEANED_FILE', 'PROCESSED_FILE', 'OUTPUT_FILE',
    'API_URL', 'API_TIMEOUT', 'MAX_TOKENS', 'STOP_SEQUENCES',
    'SPEAKER_FORMAT', 'REPETITION_PENALTY', 'TEMPERATURE',
    'TOP_P', 'TOP_K', 'MAX_SENTENCE_VALIDATION_ERRORS',
    'LOG_DIR', 'LOG_FILE', 'DEBUG_LOG_FILE',
    'PRESERVE_CASE', 'STRICT_PUNCTUATION, LOOPCHECK'
]