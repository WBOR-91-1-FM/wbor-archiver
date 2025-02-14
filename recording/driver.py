import os
import subprocess
import logging
import pytz
import time
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
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


def main():
    """
    Capture the stream as multiple segments using FFmpeg's segment muxer,
    with strftime placeholders in filename to include the current date and time.
    Before starting, sleep until the next segment boundary.
    """

    # Ensure ARCHIVE_DIR exists
    try:
        if not os.path.exists(ARCHIVE_DIR):
            os.makedirs(ARCHIVE_DIR, exist_ok=True)
    except Exception as e:
        logging.error(f"Failed to create archive directory '{ARCHIVE_DIR}': {e}")
        exit(1)

    pattern = os.path.join(ARCHIVE_DIR, f"{STATION_ID}-%Y-%m-%d_%H_%M_%S.mp3")

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
                f"Sleeping for {sleep_time} seconds until next segment boundary ({boundary_time.strftime('%Y-%m-%d_%H_%M_%S')})..."
            )
            time.sleep(sleep_time)
            logging.info("Woke up at the segment boundary.")
    except Exception as e:
        logging.error(f"Error in time calculation: {e}")
        exit(1)

    # Build the FFmpeg command
    cmd = [
        "ffmpeg",
        "-i",
        STREAM_URL,
        "-c:a",
        "copy",  # Copy the stream directly (it's already MP3)
        "-f",
        "segment",  # Use the segment muxer
        "-strftime",
        "1",  # Enable strftime placeholders, which is needed for the pattern
        "-segment_time",
        str(SEGMENT_DURATION_SECONDS),
        pattern,
    ]

    logging.info("Running FFmpeg command: " + " ".join(cmd))
    # This command will run indefinitely, creating new files at each segment boundary
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg failed with error: {e}")
        exit(1)
    except FileNotFoundError:
        logging.error(
            "FFmpeg executable not found. Make sure FFmpeg is installed and in the system PATH."
        )
        exit(1)
    except Exception as e:
        logging.error(f"Unexpected error while running FFmpeg: {e}")
        exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Process interrupted by user. Exiting gracefully.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        exit(1)
