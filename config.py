# Chunk processing configuration
CHUNK_SIZE = 250                  # Reduced chunk size for better formatting accuracy
CHUNK_OVERLAP = 100                # Reduced overlap for cleaner transitions
OUTPUT_CHUNK_SIZE = 150           # Words to output from each processed chunk

# Text processing parameters
MIN_SENTENCE_LENGTH = 5           # Reduced minimum for shorter sentences
MAX_FRAGMENT_LENGTH = 60          # Reduced to prevent run-on sentences
SENTENCE_MARKER = chr(0x0a)       # Unicode character to mark sentence boundaries

# File paths
INPUT_FILE = 'files/transcript.txt'
CLEANED_FILE = 'files/transcript_preprocessed.txt'
PROCESSED_FILE = 'files/transcript_processed.txt'
POSTPROCESSED_FILE = 'files/transcript_postprocessed.txt'
OUTPUT_FILE = 'files/transcript_formatted.txt'

# API configuration
API_URL = "http://0.0.0.0:5000/v1/completions"
API_TIMEOUT = 90                 # Increased timeout for complex formatting
MAX_TOKENS = 700                 # Increased token limit for better context
STOP_SEQUENCES = ["\n\n", "###", "##", "</end>", "Text:"]

# Formatting templates
SPEAKER_FORMAT = "{name}: {content}"

# Language model parameters
REPETITION_PENALTY = 1.2
TEMPERATURE = 0.1
TOP_P = 0.95
TOP_K = 50
TOP_T = TOP_K

# Validation and logging
MAX_SENTENCE_VALIDATION_ERRORS = 5  # More lenient validation
LOG_DIR = 'logs'
LOG_FILE = 'runlog.log'
DEBUG_LOG_FILE = 'debug.log'

# Special processing flags
PRESERVE_CASE = True              # Preserve original capitalization
STRICT_PUNCTUATION = False        # More flexible punctuation handling

# Debug flags
FORMATCHECK = False
LINECHECK = False


__all__ = [
    'CHUNK_SIZE', 'CHUNK_OVERLAP', 'OUTPUT_CHUNK_SIZE','POSTPROCESSED_FILE',
    'MIN_SENTENCE_LENGTH', 'MAX_FRAGMENT_LENGTH', 'SENTENCE_MARKER',
    'INPUT_FILE', 'CLEANED_FILE', 'PROCESSED_FILE', 'OUTPUT_FILE',
    'API_URL', 'API_TIMEOUT', 'MAX_TOKENS', 'STOP_SEQUENCES',
    'SPEAKER_FORMAT', 'REPETITION_PENALTY', 'TEMPERATURE',
    'TOP_P', 'TOP_K', 'MAX_SENTENCE_VALIDATION_ERRORS',
    'LOG_DIR', 'LOG_FILE', 'DEBUG_LOG_FILE', 'FORMATCHECK',
    'PRESERVE_CASE', 'STRICT_PUNCTUATION', 'LINECHECK'
]