# Transcript Formatter

## Overview
This project is intended to processes long unformatted text files (such as a raw audio transcripts) converting them into 
formatted content with complete sentences.


## Key Features

- Converts raw unformatted transcripts into readable, well-structured text.
- Handles text of any length using chunked processing.
- Produces output with punctuation of sentences
- Un-formatted fragments remain unchanged.

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

   Run the formatter:
   ```bash
   python process.py
   * config.py defines file paths
   ```

## How It Works

### The system:
- Processes text in chunks that fit within the LLM's context window  
- Applies proper formatting to each chunk  
- Combines chunks results correctly 
- Preserves the original content's meaning and intent  

### Output Format:
- Proper sentence structure with correct punctuation  

### Technical Approach:
- Uses chunked processing to handle unlimited length input  
- Maintains overlap between chunks for seamless transitions  

### Status:
- Preliminary results shows that a LoRA will need to be trained.
- Proper chunking and combining of chunks is essential and is the current priority.
- Proper chunking facilitates the production of training data.