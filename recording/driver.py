"""
This script captures a stream from a given URL and segments it into multiple files for archiving and playback.
Files are segmented with future concatenation in mind, so gapless playback is possible. As a result, FFmpeg
is unable to split the stream exactly at the segment boundary, but it will be very close (+/- some seconds).

This is brittle in the sense that we're relying on FFmpeg's logging to determine when a segment is
"complete"/has finished writing. If FFmpeg changes its logging format, this script may break.

Furthermore, if FFmpeg is killed or crashes, this script does not handle errors gracefully. We're 
relying on Docker's restart policy to restart the container (and spin up a new process) if it exits.
Consequently, there will be a final `.temp` file that will never get renamed with `.mp3`. To address this,
we could implement a cleanup process that runs periodically to rename any `.temp` files that are older
than a certain threshold (e.g. 1 hour) to `.mp3` files, but this is not implemented at this time.

This script is designed to be run as a long-running process, and will continue to capture the stream
until it is manually stopped.
"""

import os
import subprocess
import re
import threading
import logging
import pytz
import time
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Environment variables
try:
    STATION_ID = os.environ.get("STATION_ID", "wbor").upper()
    STREAM_URL = os.environ.get("STREAM_URL", "https://listen.wbor.org/")
    ARCHIVE_DIR = os.environ.get(
        "ARCHIVE_DIR", "/archive"
    )  # Use an absolute path for the archive directory
    SEGMENT_DURATION_SECONDS = int(os.environ.get("SEGMENT_DURATION_SECONDS", 300))
    TZ = pytz.timezone(
        os.environ.get("TZ", "America/New_York")
    )  # https://en.wikipedia.org/wiki/List_of_tz_database_time_zones?useskin=vector
except Exception as e:
    logging.error(f"Failed to load environment variables: {e}")
    exit(1)


previous_segment_temp = None  # Path to the previous segment file


def rename_temp_to_mp3(temp_path: str):
    """
    Replaces the .temp extension with .mp3 and renames the file.
    Returns the new (final) path if successful, or None on error.
    """
    if not temp_path.endswith(".temp"):
        return None

    final_path = temp_path.rsplit(".temp", 1)[0] + ".mp3"
    if os.path.exists(temp_path):
        try:
            os.rename(temp_path, final_path)
            logging.info(f"[Monitor] Renamed '{temp_path}' -> '{final_path}'")
            return final_path
        except Exception as e:
            logging.error(f"Failed to rename {temp_path} -> {final_path}: {e}")
            return None
    else:
        logging.warning(f"[Monitor] Could not find file to rename: {temp_path}")
        return None


def ffmpeg_business_logic(log_line: str):
    """
    Test if the log line is an 'Opening' segment line and if so, mark the previous segment as complete.
    """
    global previous_segment_temp

    # Example: [segment @ ...] Opening '/archive/WBOR-2025-02-14_00_44_58.temp' for writing
    regex_opening = re.compile(r"Opening '([^']+\.temp)' for writing")
    match = regex_opening.search(log_line)
    if match:
        new_segment_filename = match.group(1)
        logging.info(f"[Monitor] New segment detected: {new_segment_filename}")

        # At this point, we know the *previous* segment is fully written/closed
        # So we can rename it to .mp3
        if previous_segment_temp:
            rename_temp_to_mp3(previous_segment_temp)

        # Update pointer to the new (current) segment
        # If this is the first segment, previous_segment_temp will be None
        previous_segment_temp = new_segment_filename


def ffmpeg_log_handler(ffmpeg_process: subprocess.Popen):
    """
    Read FFmpeg's stderr line by line, parse, and apply business logic.

    (By default, FFmpeg prints most logging and progress messages to stderr)
    """
    for line in ffmpeg_process.stderr:
        logging.debug("[FFmpeg] %s", line.strip())
        ffmpeg_business_logic(line.strip())


def main():
    """
    Capture the stream as multiple segments using FFmpeg's segment muxer,
    with strftime placeholders in filename to include the current date and time.
    Waits to reach the next segment boundary before starting the recording process.
    (e.g. if it is 3:12:34 and SEGMENT_DURATION_SECONDS is 300, it will wait until 3:15:00)

    Due to the way segmenting works, it ffmpeg may not split the stream exactly at the
    segment boundary, but it will be very close (+/- 3 seconds).

    Output files will be named similar to:
    - `WBOR-2025-02-14_00_35_01.mp3`
    - `WBOR-2025-02-14_00_40_00.mp3`
    - `WBOR-2025-02-14_00_44_58.mp3`
    """

    # Ensure ARCHIVE_DIR exists
    try:
        if not os.path.exists(ARCHIVE_DIR):
            os.makedirs(ARCHIVE_DIR, exist_ok=True)
    except Exception as e:
        logging.error(f"Failed to create archive directory '{ARCHIVE_DIR}': {e}")
        exit(1)

    # Use .temp extension in the pattern
    # e.g.: /archive/WBOR-2025-02-14_00_40_00.temp
    pattern = os.path.join(ARCHIVE_DIR, f"{STATION_ID}-%Y-%m-%d_%H_%M_%S.temp")

    logging.info(f"Segment duration set to: {SEGMENT_DURATION_SECONDS} seconds")
    logging.info(f"Writing segments to pattern: {pattern}")

    # Calculate how many seconds to sleep until the next segment boundary
    try:
        now = datetime.now(TZ)
        seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second
        remainder = seconds_since_midnight % SEGMENT_DURATION_SECONDS
        if remainder:
            sleep_time = SEGMENT_DURATION_SECONDS - remainder
            boundary_time = now + timedelta(seconds=sleep_time)

            logging.info(
                f"Current time is {now.strftime('%Y-%m-%d_%H_%M_%S')}. "
                f"Sleeping until next segment boundary at {boundary_time.strftime('%Y-%m-%d_%H_%M_%S')}"
            )
            time.sleep(sleep_time)
            logging.info("Segment boundary reached. Starting recording...")
    except Exception as e:
        logging.error(f"Error in time calculation: {e}")
        exit(1)

    # Build the FFmpeg command
    cmd = [
        "ffmpeg",
        "-i",
        STREAM_URL,
        "-map",
        "0:a",  # Map the audio stream explicitly since we're using `.temp` extension in pattern
        "-c:a",
        "copy",  # Copy the stream directly (already MP3)
        "-f",
        "segment",  # Use the segment muxer
        "-segment_format",
        "mp3",
        "-strftime",
        "1",  # Enable strftime placeholders, which is needed for the pattern
        "-segment_time",
        str(SEGMENT_DURATION_SECONDS),
        "-segment_time_metadata",
        "1",  # Embed segment timing metadata
        pattern,
    ]
    # segment_time_metadata: If set to 1, every packet will contain the lavf.concat.start_time and the lavf.concat.duration packet metadata values which are the start_time and the duration of the respective file segments in the concatenated output expressed in microseconds. The duration metadata is only set if it is known based on the concat file. The default is 0.

    logging.info("Running FFmpeg: " + " ".join(cmd))

    try:
        # Spawn the FFmpeg process
        ffmpeg_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,  # Might be unused for audio, but included for completeness
            stderr=subprocess.PIPE,
            text=True,
        )

        # Start a thread to monitor FFmpeg's output
        t = threading.Thread(
            target=ffmpeg_log_handler, args=(ffmpeg_process,), daemon=True
        )
        t.start()

        # Wait for FFmpeg to exit (this call will block until FFmpeg stops, which ideally never happens).
        ffmpeg_returncode = ffmpeg_process.wait()
        if ffmpeg_returncode != 0:
            logging.error(f"FFmpeg exited with a non-zero code: {ffmpeg_returncode}")
            exit(1)
    except FileNotFoundError:
        logging.error(
            "FFmpeg not found. Make sure it's installed and in the system PATH."
        )
        exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Process interrupted by user. Exiting gracefully.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        exit(1)
