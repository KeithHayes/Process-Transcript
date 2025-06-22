# Transcript Formatter

## Overview
This project processes long passages of unformatted text (such as audio transcripts) and converts them into properly formatted content with complete sentences and paragraphs, while maintaining faithfulness to the original content.

## Key Features
- Converts raw transcripts into readable, well-structured text
- Maintains original meaning while improving formatting
- Handles text of any length using chunked processing
- Produces essay-style output with proper punctuation and paragraphs

## Installation & Setup

### Prerequisites
- Python 3.8+
- Virtual environment (recommended)

### Server Setup

1. Start the server (provides the loaded model):
   ```bash
   python server.py
   ```

2. The OpenAI-compatible API will be available at:
   ```
   http://0.0.0.0:5000
   ```

### Running the Formatter

1. Activate your virtual environment:

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
- Logical paragraph breaks  
- Speaker identification (when present in source)  
- Removal of filler words (uh, um, etc.)  
- Consistent capitalization  

### Technical Approach:
- Uses chunked processing to handle unlimited length input  
- Maintains overlap between chunks for seamless transitions  
- Applies post-processing for consistent formatting  
- Includes fallback basic formatting if LLM processing fails  
