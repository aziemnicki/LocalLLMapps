# YouTube Notes and Multimodal RAG

This repository contains two main components:

## 1. YouTube Notes

The `YouTube notes/app.py` script is designed to monitor a specified YouTube playlist and generate summaries of the videos within that playlist. It utilizes the following features:

- **Video ID Retrieval**: The script retrieves video IDs from a specified YouTube playlist using the `pytubefix` library.
- **Transcript Extraction**: It extracts transcripts from the videos using the `youtube_transcript_api`, supporting multiple languages.
- **Chunking**: The transcripts are split into manageable chunks based on a specified maximum duration.
- **Summarization**: Each chunk is summarized using the Gemma-3 model via the `ollama` library, producing concise summaries relevant to data science and AI.
- **Markdown File Creation**: The generated summaries are saved as markdown files in a specified output directory.

### Configuration

- `MODEL_NAME`: The name of the model to be used for summarization (default is "gemma3").
- `CHECK_INTERVAL`: The interval at which the script checks for new videos (default is 10 minutes).
- `OUTPUT_DIR`: The directory where markdown files are saved.

### Usage

To run the script, ensure you have the necessary libraries installed and execute it in a Python environment.

## 2. Multimodal RAG

The `Multimodal RAG/app.py` script serves as an AI assistant that processes both text and images. Key features include:

- **Image Processing**: Users can upload images, which are converted to base64 format for processing.
- **Chat Interface**: The assistant provides a chat interface using Streamlit, allowing users to interact with the AI model.
- **Session Management**: The application maintains session states for text and image messages, enabling a smooth user experience.
- **Error Handling**: The script includes error handling to manage issues during model queries or image processing.

### Configuration

- The application is configured to use the Gemma-3 model for generating responses and summaries.

### Usage

To run the assistant, ensure you have Streamlit installed and execute the script in a Python environment.

## Installation

To install the required packages, run:

```bash
pip install -r requirements.txt