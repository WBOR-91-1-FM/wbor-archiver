"""
Capture an MP3 audio stream from a URL and segment it into multiple
files for archiving and playback. Files are segmented with future
concatenation in mind, so gapless playback is possible. As a result,
FFmpeg is unable to split the stream at *exactly* the segment boundary,
but it will be very close (~ +/- 10s).

This is brittle in that we're relying on FFmpeg's logs to determine when
a segment is "complete" (has finished writing).

NOTE: If FFmpeg changes its logging format, this script may break!

As the segment is being written, it will have a `.temp` extension to
indicate that it is "in progress". Once writing has finished, the file
will be renamed to `.mp3`. This is done to prevent incomplete files from
misidentified as valid (complete) segments.

If FFmpeg is killed or crashes, this script does not handle errors
gracefully. We rely on Docker's restart policy (`always`) to restart the
container and spin up a new process. Consequently, if the next segment
never arrives, there will be a final `.temp` file that will never be
closed as an `.mp3`. This `.temp` file is actually a valid (albeit
partial) MP3. Perhaps it would be worth it to keep these files around
with a flag to indicate that they are incomplete.

Files will be named in ISO 8601 UTC format, for example:
- `WBOR-2025-02-14T00:35:01Z.mp3`
- `WBOR-2025-02-14T00:40:00Z.mp3`
"""

import logging
import os
import re
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta

import pytz
from dotenv import load_dotenv

FORMAT_STR = (
    "%(asctime)s - %(levelname)s - "
    "[%(filename)s:%(lineno)d in %(funcName)s()] - %(message)s"
)

logging.basicConfig(
    level=logging.DEBUG,
    format=FORMAT_STR,
)

load_dotenv()

try:
    STATION_ID = os.getenv("STATION_ID").strip().upper()
    STREAM_URL = os.getenv("STREAM_URL").strip()
    ARCHIVE_DIR = os.getenv("ARCHIVE_DIR").strip()
    segment_duration_str = os.getenv("SEGMENT_DURATION_SECONDS").strip()
    if not segment_duration_str.isdigit():
        raise ValueError(
            f"SEGMENT_DURATION_SECONDS must be an integer, got '{segment_duration_str}'"
        )
    SEGMENT_DURATION_SECONDS = int(segment_duration_str)

    # Use UTC timezone for consistency
    TZ = pytz.UTC

    logging.debug(
        "Configuration loaded successfully: "
        "STATION_ID=`%s`, STREAM_URL=`%s`, ARCHIVE_DIR=`%s`, SEGMENT_DURATION_SECONDS=`%d`",
        STATION_ID,
        STREAM_URL,
        ARCHIVE_DIR,
        SEGMENT_DURATION_SECONDS,
    )
except (ValueError, AttributeError, TypeError) as e:
    logging.error("Failed to load environment variables: `%s`", e)
    sys.exit(1)

# ISO UTC formatting pattern (ex: `WBOR-2025-02-14T00:40:00Z.temp`)
PATTERN = os.path.join(ARCHIVE_DIR, f"{STATION_ID}-%Y-%m-%dT%H:%M:%SZ.temp")

# Build the FFmpeg command
CMD = [
    "env",
    "TZ=UTC",
    "ffmpeg",
    "-loglevel",
    "verbose",
    "-i",
    STREAM_URL,
    "-map",
    "0:a",  # Map the audio stream explicitly since we're using `.temp`
    "-c:a",
    "copy",  # Copy the stream directly (assumed to already be MP3)
    "-f",
    "segment",  # Use the segment muxer
    "-segment_format",
    "mp3",
    "-strftime",
    "1",  # Enable strftime placeholders for the pattern
    "-segment_time",
    str(SEGMENT_DURATION_SECONDS),
    "-segment_time_metadata",
    "1",  # Embed segment timing metadata
    PATTERN,
]


def rename_temp_to_mp3(temp_path: str):
    """
    Replaces the `.temp` extension with `.mp3`.
    Returns the new path if successful, or None on error.
    """
    if not temp_path.endswith(".temp"):
        logging.warning("Path does not end with .temp: `%s`", temp_path)
        return None

    if not os.path.exists(temp_path):
        logging.warning("Could not find file to rename: `%s`", temp_path)
        return None

    try:
        final_path = temp_path.rsplit(".temp", 1)[0] + ".mp3"
        os.rename(temp_path, final_path)
        logging.debug("Renamed `%s` -> `%s`", temp_path, final_path)
        return final_path
    except (OSError, subprocess.SubprocessError) as e:
        logging.error("Failed to rename `%s` -> `%s`: %s", temp_path, final_path, e)
        return None


def business_logic(log_line: str, active_segment: str):
    """
    Check if the logs indicates a segment has ended; `.temp` -> `.mp3`.

    If a new segment is detected, return the new segment path.
    Otherwise, return the previous (current) segment path.

    Parameters:
    - log_line: A single line of FFmpeg's stderr output.
    - active_segment: The current segment file that is being written to.
    """
    # Detect that a segment has ended and rename the file.
    # Example:
    # `segment:'/archive/WBOR-2025-02-17T13:30:00Z.temp' count:0 ended`
    match_ended = re.search(r"segment:'([^']+\.temp)' count:(\d+) ended", log_line)
    if match_ended:
        ended_segment_path = match_ended.group(1)
        segment_count = int(match_ended.group(2))
        closed_path = rename_temp_to_mp3(ended_segment_path)
        logging.info(
            "Segment #%d ended: `%s`. Renamed to: `%s`",
            segment_count,
            ended_segment_path,
            closed_path,
        )

    # Detect when FFmpeg opens a new segment for writing.
    # Example:
    # `Opening '/archive/WBOR-2025-02-17T13:35:00Z.temp' for writing`
    match_opening = re.search(r"Opening '([^']+\.temp)' for writing", log_line)
    if match_opening:
        new_segment_temp = match_opening.group(1)
        logging.info("New segment detected: `%s`", new_segment_temp)
        return new_segment_temp

    # Detect Metadata updates for StreamTitle
    # Example: `Metadata update for StreamTitle: Queen - Cool Cat`
    match_metadata = re.search(r"Metadata update for StreamTitle: (.+)", log_line)
    if match_metadata:
        stream_title = match_metadata.group(1)
        logging.info("Stream title updated: `%s`", stream_title)

    # Unchanged; leave the previous segment temp unchanged
    return active_segment


class Recorder:
    """
    Instantiate the Recorder class to capture the stream.
    This class handles the FFmpeg process, signal handling, and
    segmenting logic.
    """

    def __init__(self):
        self.ffmpeg_process = None
        self.active_segment = None

    def handle_signal(self, signum, _frame):
        """
        Signal handler that attempts a graceful shutdown.
        """
        logging.info("Received signal `%d` - initiating graceful shutdown", signum)
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            logging.info("Sending SIGTERM to FFmpeg process group")
            os.killpg(self.ffmpeg_process.pid, signal.SIGTERM)
            try:
                # Use a shorter timeout to exit faster
                self.ffmpeg_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logging.warning(
                    "FFmpeg did not exit after SIGTERM - sending SIGKILL to process group"
                )
                os.killpg(self.ffmpeg_process.pid, signal.SIGKILL)
        sys.exit(0)

    def ffmpeg_log_handler(self):
        """
        Reads FFmpeg's stderr line by line, applying business logic to
        update the current segment.

        (By default, FFmpeg prints logging and progress messages to
        stderr)
        """
        try:
            # Ensure process is still running
            while self.ffmpeg_process.poll() is None:
                line = self.ffmpeg_process.stderr.readline()
                if not line:
                    break  # Stop reading if no more lines are available
                logging.debug("%s", line.strip())  # Raw log line

                # As FFmpeg logs are read, apply business logic to
                # handle segmenting
                # `active_segment` is updated with the current segment
                # file that is being written to.
                # If it is determined that a segment has ended, the file
                # is renamed and the `active_segment` is updated to the
                # new segment file.

                self.active_segment = business_logic(line.strip(), self.active_segment)
        except ValueError:
            logging.warning(
                "FFmpeg log handler tried to read from a closed stderr stream."
            )

    def assert_archive_dir_exists(self):
        """
        Check that the archive directory exists; create it if necessary.
        """
        try:
            if not os.path.exists(ARCHIVE_DIR):
                os.makedirs(ARCHIVE_DIR, exist_ok=True)
        except OSError as e:
            logging.error("Failed to create archive directory `%s`: %s", ARCHIVE_DIR, e)
            sys.exit(1)
        return True

    def time_until_next_segment(self):
        """
        Compute time (in seconds) until the next segment boundary.
        """
        try:
            now = datetime.now(TZ)
            seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second
            remainder = seconds_since_midnight % SEGMENT_DURATION_SECONDS

            if remainder or now.second != 0:
                # Calculate sleep time to reach the next segment
                sleep_time = (
                    SEGMENT_DURATION_SECONDS - remainder
                    if remainder
                    else SEGMENT_DURATION_SECONDS
                )
                boundary_time = now + timedelta(seconds=sleep_time)
                logging.info(
                    "Current time is `%s`. Sleeping until next segment boundary at `%s`",
                    now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    boundary_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                )
                return sleep_time
            return 0
        except (ValueError, OverflowError) as e:
            logging.error("Error calculating time until next segment: `%s`", e)
            sys.exit(1)

    def run(self):
        """
        Capture the STREAM_URL as multiple segments using FFmpeg's
        segment muxer, with strftime placeholders in the filename to
        include the current date and time.

        Waits to reach the next segment boundary before starting the
        recording process. (e.g. if it is 3:12:34 and
        SEGMENT_DURATION_SECONDS is 300, it will wait until 3:15:00)

        Due to the way segmenting works, ffmpeg may not split the stream
        exactly at the segment boundary, but it will be very close (~
        +/- 10 seconds).

        The segments are named with ISO 8601 UTC timestamps (e.g.
        `WBOR-2025-02-14T00:40:00Z.mp3`). This is done to ensure that
        the files are named in a consistent and unambiguous way, and to
        prevent issues with timezones or file name conflicts down the
        road.
        """
        if not self.assert_archive_dir_exists():
            logging.critical("Failed to create archive directory. Exiting.")
            sys.exit(1)

        logging.debug(
            "Segment duration set to: `%d` seconds (`%.1f` minutes)",
            SEGMENT_DURATION_SECONDS,
            SEGMENT_DURATION_SECONDS / 60,
        )
        logging.debug("Writing segments according to pattern: `%s`", PATTERN)

        time.sleep(self.time_until_next_segment())
        logging.info("Segment boundary reached. Starting recording...")
        logging.info("Running FFmpeg: `%s`", " ".join(CMD))

        try:
            self.ffmpeg_process = subprocess.Popen(
                CMD,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True,
                bufsize=1,  # Line buffering for realtime processing
                start_new_session=True,  # Launch in a new process group
            )

            # Start log handler thread (daemon so it exits when the main thread does)
            t = threading.Thread(target=self.ffmpeg_log_handler, daemon=True)
            t.start()

            # Wait for FFmpeg to finish
            ffmpeg_returncode = self.ffmpeg_process.wait()
            if ffmpeg_returncode != 0:
                logging.error(
                    "FFmpeg exited unexpectedly. Terminating log handler thread."
                )
                sys.exit(1)
            logging.info("FFmpeg process exited with code: `%d`", ffmpeg_returncode)
        except FileNotFoundError:
            logging.error(
                "FFmpeg not found. Make sure it's installed and in the system PATH."
            )
            sys.exit(1)
        except (subprocess.SubprocessError, OSError) as e:
            logging.error("Unexpected error: `%s`", e)
            sys.exit(1)


if __name__ == "__main__":
    try:
        recorder = Recorder()

        def signal_handler(signum, frame):
            """
            Handle signals for graceful shutdown.
            """
            recorder.handle_signal(signum, frame)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        recorder.run()
    except KeyboardInterrupt:
        logging.info("Process interrupted by user. Exiting gracefully.")
    except (OSError, subprocess.SubprocessError) as e:
        logging.error("Unexpected error: `%s`", e)
        sys.exit(1)
