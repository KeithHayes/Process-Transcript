# Chunk processing configuration
CHUNK_SIZE = 200                  # Slightly smaller chunks for better quality
CHUNK_OVERLAP = 75                # Increased overlap for smoother transitions
OUTPUT_CHUNK_SIZE = 125           # Adjusted output size

# Text processing parameters
MIN_SENTENCE_LENGTH = 6           # Balanced minimum length
MAX_FRAGMENT_LENGTH = 35          # Allows for moderate-length sentences
SENTENCE_MARKER = chr(0x0a)       # Unicode character for boundaries

# File paths (unchanged)
SAVEDCHUNKS = 'files/savedchunks'
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
# EXPANDED STOP_SEQUENCES to prevent LLM injecting unwanted instructional text
STOP_SEQUENCES = [
    "\n\n", "###", "##", "</end>", "Text:", "Formatted text:",
    "the formatted output should follow these guidelines",
    "each complete sentence must start on a new line",
    "proper nouns like alice are capitalized",
    "punctuation marks such as periods commas question marks exclamation points",
    "quoted material longer than four lines should be indented"
]

# Language model parameters
REPETITION_PENALTY = 1.2          # Balanced repetition control
TEMPERATURE = 0.15                # Lower temperature for consistency
TOP_P = 0.9                       # Focused sampling
TOP_K = 50                        # Balanced predictability
TOP_T = TOP_K # Retained TOP_T = TOP_K as it was in your original config. If your API doesn't use it, it will be ignored.

# Validation and logging
MAX_SENTENCE_VALIDATION_ERRORS = 3  # Stricter validation
LOG_DIR = 'logs'
LOG_FILE = 'runlog.log'
DEBUG_LOG_FILE = 'debug.log'

# Special processing flags
PRESERVE_CASE = True              # Maintain original capitalization
STRICT_PUNCTUATION = True         # Enforce proper punctuation
PRESERVE_PARAGRAPHS = True        # Maintain paragraph structure

# Debug flags
FORMATCHECK = False
LINECHECK = False

# Quality control
MIN_SENTENCE_QUALITY = 0.8        # Higher quality threshold
MAX_RETRIES = 3                   # More retry attempts for poor formatting
TEST_MODE = "run"

__all__ = [
    'CHUNK_SIZE', 'CHUNK_OVERLAP', 'OUTPUT_CHUNK_SIZE', 'POSTPROCESSED_FILE',
    'MIN_SENTENCE_LENGTH', 'MAX_FRAGMENT_LENGTH', 'SENTENCE_MARKER',
    'INPUT_FILE', 'CLEANED_FILE', 'PROCESSED_FILE', 'OUTPUT_FILE',
    'API_URL', 'API_TIMEOUT', 'MAX_TOKENS', 'STOP_SEQUENCES',
    'REPETITION_PENALTY', 'TEMPERATURE', 'TOP_P', 'TOP_K', 'TOP_T', # TOP_T included in __all__
    'MAX_SENTENCE_VALIDATION_ERRORS', 'LOG_DIR', 'LOG_FILE',
    'DEBUG_LOG_FILE', 'FORMATCHECK', 'PRESERVE_CASE',
    'STRICT_PUNCTUATION', 'PRESERVE_PARAGRAPHS', 'LINECHECK',
    'MIN_SENTENCE_QUALITY', 'MAX_RETRIES', 'TEST_MODE'
]