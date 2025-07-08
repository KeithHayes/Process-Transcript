# Transcript Formatter

## Overview
This project processes long unformatted text files (such as audio transcripts) and converts them into properly formatted content with complete sentences.

Future processing intends to use cosine similarity to build paragraphs from sentences.

## Key Features

- Converts raw unformatted transcripts into readable, well-structured text.
- Maintains content without change.
- Handles text of any length using chunked processing.
- Produces output with proper punctuation of sentences and un-formatted fragments.

## Installation & Setup

### Prerequisites
- Python 3.8+
- The text-generation-webui sever and a loaded model, currently developing with mythomax gguf variants.

### Server Setup

1. Start the server (provides the loaded model):
   ```bash
   python server.py
   ```

2. The OpenAI-compatible API will be available at:
   ```
   http://0.0.0.0:5000

3. Use the webui to load a model.
   ```

### Running the Formatter

1. Activate your virtual environment if you build one:

   **Linux/Mac:**
   ```bash
   source venv/bin/activate
   ```

   **Windows:**
   ```cmd
   venv\Scripts\activate
   ```

2. Run the formatter:
   ```bash
   python run.py
   ```

## How It Works

### The system:
- Processes text in chunks that fit within the LLM's context window  
- Applies proper formatting to each chunk  
- Intelligently combines results while maintaining smooth transitions  
- Preserves the original content's meaning and intent  

### Output Format:
- Proper sentence structure with correct punctuation  


### Technical Approach:
- Uses chunked processing to handle unlimited length input  
- Maintains overlap between chunks for seamless transitions  

