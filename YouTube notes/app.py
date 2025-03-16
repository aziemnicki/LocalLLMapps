import streamlit as st
import os
import re
import time
import threading
import pytubefix
import ollama
from youtube_transcript_api import YouTubeTranscriptApi
from datetime import datetime

# Configuration
MODEL_NAME = "gemma3"  # Model name in Ollama
CHECK_INTERVAL = 600  # Check for new videos every 10 minutes (in seconds)
OUTPUT_DIR = "summaries"  # Directory for markdown files
MAX_CHUNK_DURATION = 15 * 60  # Maximum chunk duration in seconds (15 minutes)

# Create output directory if it doesn't exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


# Function to get video IDs from a playlist
def get_playlist_videos(playlist_url):
    try:
        pl = pytubefix.Playlist(playlist_url)
        # Force download of all videos in the playlist
        pl._video_urls = []  # Reset cache
        video_ids = [video.video_id for video in pl.videos]
        return video_ids, pl.title
    except Exception as e:
        st.error(f"Error while downloading playlist: {e}")
        return [], ""


# Function to get transcript
def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["pl", "en"]
        )
        full_transcript = " ".join([entry["text"] for entry in transcript_list])
        timestamps = [entry["start"] for entry in transcript_list]
        return full_transcript, transcript_list, timestamps
    except Exception as e:
        st.error(f"Error while downloading transcript: {e}")
        return "", [], []


# Function to split transcript into chunks
def split_transcript_by_time(transcript_list, max_duration=MAX_CHUNK_DURATION):
    chunks = []
    current_chunk = []
    current_duration = 0
    start_time = 0

    for entry in transcript_list:
        if current_duration == 0:
            start_time = entry["start"]

        current_chunk.append(entry["text"])
        current_duration = entry["start"] - start_time + entry["duration"]

        if current_duration >= max_duration:
            chunks.append(
                {
                    "text": " ".join(current_chunk),
                    "start_time": start_time,
                    "duration": current_duration,
                }
            )
            current_chunk = []
            current_duration = 0

    # Add last chunk if it exists
    if current_chunk:
        chunks.append(
            {
                "text": " ".join(current_chunk),
                "start_time": start_time,
                "duration": current_duration,
            }
        )

    return chunks


# Function to generate summary for a chunk using Ollama
def summarize_chunk(chunk_text, video_title, chunk_index):
    prompt = f"""
    The text below is a transcript of a video "{video_title}" (part {chunk_index + 1}).
    
    TRANSCRIPT:
    {chunk_text}
    
    Summarize the most important information from this transcript in 3-5 points that are relevant to a data scientist 
    working with AI. Focus on practical tips, techniques, concepts, and tools.
    Each point should be brief and concrete.
    """

    try:
        response = ollama.chat(
            model=MODEL_NAME, messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"]
    except Exception as e:
        st.error(f"Error while generating summary: {e}")
        return "Error while generating summary."


# Function to generate overall summary for a video
def generate_overall_summary(video_title, all_summaries):
    combined_summaries = "\n\n".join(all_summaries)

    prompt = f"""
    The text below is a collection of summaries of a video "{video_title}".
    
    SUMMARIES:
    {combined_summaries}
    
    Based on these summaries, generate an overall summary of the video in 5-7 points.
    The summary should contain the most important concepts, tools, and techniques from the video,
    as well as 3-5 keywords/tags related to the video content in the format [[tag]].
    """

    try:
        response = ollama.chat(
            model=MODEL_NAME, messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"]
    except Exception as e:
        st.error(f"Error while generating overall summary: {e}")
        return "Error while generating overall summary."


# Function to create markdown file with summary
def create_markdown_summary(
    video_id, video_title, overall_summary, chunk_summaries, chunks
):
    # Prepare filename (replace disallowed characters)
    safe_title = re.sub(r'[\\/*?:"<>|]', "", video_title)
    filename = f"{OUTPUT_DIR}/{safe_title}_{datetime.now().strftime('%Y%m%d')}.md"

    with open(filename, "w", encoding="utf-8") as f:
        # Header
        f.write(f"# {video_title}\n\n")
        f.write(f"Link: [YouTube](https://www.youtube.com/watch?v={video_id})\n")
        f.write(f"Summary date: {datetime.now().strftime('%Y-%m-%d')}\n\n")

        # Overall summary
        f.write("## Overall summary\n\n")
        f.write(f"{overall_summary}\n\n")

        # Summaries of individual chunks
        f.write("## Summaries of individual chunks\n\n")
        for i, (summary, chunk) in enumerate(zip(chunk_summaries, chunks)):
            start_time_formatted = time.strftime(
                "%H:%M:%S", time.gmtime(chunk["start_time"])
            )
            f.write(f"### Chunk {i + 1} (from {start_time_formatted})\n\n")
            f.write(f"{summary}\n\n")


# Function to monitor playlist and process new videos
def monitor_playlist(playlist_url, processed_videos):
    video_ids, playlist_title = get_playlist_videos(playlist_url)

    if not video_ids:
        st.warning("Failed to download videos from playlist. Check URL or permissions.")
        return processed_videos

    new_videos = [vid for vid in video_ids if vid not in processed_videos]

    if new_videos:
        st.info(f"Found {len(new_videos)} new videos to process.")

    for video_id in new_videos:
        try:
            # Get video information
            video = pytubefix.YouTube(f"https://www.youtube.com/watch?v={video_id}")
            video_title = video.title

            st.info(f"Starting processing of video: {video_title}")

            # Get transcript
            full_transcript, transcript_list, timestamps = get_transcript(video_id)

            if not transcript_list:
                st.warning(f"No transcript found for video: {video_title}")
                # Add to processed videos even if there's no transcript, to avoid retrying
                processed_videos.append(video_id)
                continue

            # Split transcript into chunks
            chunks = split_transcript_by_time(transcript_list)

            # Generate summaries for each chunk
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                st.info(
                    f"Processing chunk {i + 1}/{len(chunks)} of video: {video_title}"
                )
                summary = summarize_chunk(chunk["text"], video_title, i)
                chunk_summaries.append(summary)

            # Generate overall summary
            st.info(f"Generating overall summary of video: {video_title}")
            overall_summary = generate_overall_summary(video_title, chunk_summaries)

            # Create markdown file
            create_markdown_summary(
                video_id, video_title, overall_summary, chunk_summaries, chunks
            )

            # Add video to processed videos
            processed_videos.append(video_id)

            # Save processed videos list
            with open(f"{OUTPUT_DIR}/processed_videos.txt", "w") as f:
                for vid in processed_videos:
                    f.write(f"{vid}\n")

            st.success(f"Processed new video: {video_title}")

        except Exception as e:
            st.error(f"Error while processing video {video_id}: {e}")

    return processed_videos


# Function to start monitoring in the background
def background_monitoring(playlist_url, stop_event, processed_videos_list):
    # Initial check
    processed_videos_list = monitor_playlist(playlist_url, processed_videos_list)

    while not stop_event.is_set():
        time.sleep(CHECK_INTERVAL)
        processed_videos_list = monitor_playlist(playlist_url, processed_videos_list)


# Streamlit interface
st.title("Monitor YouTube Playlist with AI Summaries")

# Input field for playlist URL
playlist_url = st.text_input("Enter YouTube playlist URL:")

# Initialize session state
if "monitoring" not in st.session_state:
    st.session_state.monitoring = False
    st.session_state.stop_event = threading.Event()
    st.session_state.monitor_thread = None
    st.session_state.processed_videos = []

    # Read processed videos list
    if os.path.exists(f"{OUTPUT_DIR}/processed_videos.txt"):
        with open(f"{OUTPUT_DIR}/processed_videos.txt", "r") as f:
            st.session_state.processed_videos = [line.strip() for line in f.readlines()]

# Button to start/stop monitoring
if st.button("Start" if not st.session_state.monitoring else "Stop"):
    if not st.session_state.monitoring:
        if playlist_url:
            st.session_state.stop_event.clear()
            st.session_state.monitor_thread = threading.Thread(
                target=background_monitoring,
                args=(
                    playlist_url,
                    st.session_state.stop_event,
                    st.session_state.processed_videos,
                ),
            )
            st.session_state.monitor_thread.daemon = True
            st.session_state.monitor_thread.start()
            st.session_state.monitoring = True
            st.success("Started monitoring playlist!")
        else:
            st.error("Enter a playlist URL!")
    else:
        st.session_state.stop_event.set()
        st.session_state.monitoring = False
        st.warning("Stopped monitoring playlist.")

# Button to check now
if st.button("Check now"):
    if playlist_url:
        st.session_state.processed_videos = monitor_playlist(
            playlist_url, st.session_state.processed_videos
        )
        st.success("Finished checking playlist!")
    else:
        st.error("Enter a playlist URL!")

# Display monitoring status
if st.session_state.monitoring:
    st.info(
        f"Monitoring active. Checking new videos every {CHECK_INTERVAL // 60} minutes."
    )

    # Display list of processed videos
    st.write(f"Number of processed videos: {len(st.session_state.processed_videos)}")

    # Display list of summary files
    st.write("Generated summaries:")
    for file in os.listdir(OUTPUT_DIR):
        if file.endswith(".md"):
            st.write(f"- {file}")
