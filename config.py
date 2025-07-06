# config.py
# Chunk processing configuration
CHUNK_SIZE = 180                  # Smaller chunks for better sentence detection
CHUNK_OVERLAP = 80               # Increased overlap for context
OUTPUT_CHUNK_SIZE = 100           # Smaller output chunks

# Text processing parameters
MIN_SENTENCE_LENGTH = 6           # Balanced minimum length
MAX_FRAGMENT_LENGTH = 35          # Allows for moderate-length sentences
SENTENCE_MARKER = chr(0x0a)       # Unicode character for boundaries
MAX_SENTENCE_LENGTH = 25          # Words per sentence

# Enhanced punctuation handling
STRICT_PUNCTUATION_RULES = {
    'sentence_end': r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s',
    'abbreviations': ['Mr', 'Mrs', 'Dr', 'Prof', 'St', 'Ave', 'Blvd']
}

# File paths (unchanged)
INPUT_FILE = 'files/transcript.txt'
TEST_FILE = 'files/desired_output.txt'
CLEANED_FILE = 'files/transcript_preprocessed.txt'
PROCESSED_FILE = 'files/transcript_processed.txt'
POSTPROCESSED_FILE = 'files/transcript_postprocessed.txt'
OUTPUT_FILE = 'files/transcript_formatted.txt'

# API configuration
API_URL = "http://0.0.0.0:5000/v1/completions"
API_TIMEOUT = 120                 # Increased timeout
MAX_TOKENS = 800                  # Increased token limit
STOP_SEQUENCES = ["\n\n", "###", "##", "</end>", "Text:", "Formatted text:"]

# Language model parameters
REPETITION_PENALTY = 1.3          # Balanced repetition control
TEMPERATURE = 0.15                # Lower temperature for consistency
TOP_P = 0.9                       # Focused sampling
TOP_K = 40                        # Balanced predictability
TOP_T = TOP_K

# Validation and logging
MAX_SENTENCE_VALIDATION_ERRORS = 3  # Stricter validation
LOG_DIR = 'logs'
LOG_FILE = 'runlog.log'
DEBUG_LOG_FILE = 'debug.log'

# Special processing flags
PRESERVE_CASE = True              # Maintain original capitalization
STRICT_PUNCTUATION = True         # Enforce proper punctuation
PRESERVE_PARAGRAPHS = True        # Maintain paragraph structure
PUNCTUATION_VALIDATION = True     # Enable punctuation checks

# Debug flags
FORMATCHECK = False
LINECHECK = False

# Quality control
MIN_SENTENCE_QUALITY = 0.8        # Higher quality threshold
MAX_RETRIES = 3                   # More retry attempts for poor formatting

__all__ = [
    'CHUNK_SIZE', 'CHUNK_OVERLAP', 'OUTPUT_CHUNK_SIZE', 'POSTPROCESSED_FILE',
    'MIN_SENTENCE_LENGTH', 'MAX_FRAGMENT_LENGTH', 'SENTENCE_MARKER',
    'INPUT_FILE', 'CLEANED_FILE', 'PROCESSED_FILE', 'OUTPUT_FILE',
    'API_URL', 'API_TIMEOUT', 'MAX_TOKENS', 'STOP_SEQUENCES',
    'REPETITION_PENALTY', 'TEMPERATURE', 'TOP_P', 'TOP_K', 'MAX_SENTENCE_LENGTH',
    'MAX_SENTENCE_VALIDATION_ERRORS', 'LOG_DIR', 'LOG_FILE', 'STRICT_PUNCTUATION_RULES',
    'DEBUG_LOG_FILE', 'FORMATCHECK', 'PRESERVE_CASE','TEST_FILE', 'PUNCTUATION_VALIDATION',
    'STRICT_PUNCTUATION', 'PRESERVE_PARAGRAPHS', 'LINECHECK',
    'MIN_SENTENCE_QUALITY', 'MAX_RETRIES'
]