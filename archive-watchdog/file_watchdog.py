"""
Monitors the archive directory for `.temp` -> `.mp3` renaming events,
which indicates that a new recording segment has been completed. Then,
move the file to the appropriate directory based on the ISO 8601 UTC
timestamp parsed from the filename. Handles file conflicts by
appending a counter to the filename...

...if two conflicting file names are detected, checks equality of the
files. If identical (via hash comparison), deletes the newer duplicate.
If different, appends a counter to the filename to make a unique
filename.

Not sure how to handle the case where the files are differen (in
content) but have the same filename - this is a rare edge case. Perhaps
trigger a manual review in this case? And don't serve the new file until
the review is complete.

The final syntax will be `{STATION_ID}-YYYY-MM-DDTHH:MM:SSZ.mp3`, or
`{STATION_ID}-YYYY-MM-DDTHH:MM:SSZ-{counter}.mp3` (if a conflict is
detected).

If a file is renamed to `.mp3` but does not match the expected filename
format, it is moved to an "unmatched" directory (defined in config).

After moving the file, the watchdog script notifies the backend via
RabbitMQ so that it can kick off its business logic.
"""

import fcntl
import hashlib
import logging
import os
import re
import sys
import time
from contextlib import contextmanager

import pytz
from dotenv import load_dotenv
from utils.mq_publisher import RabbitMQClient
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format=(
        "%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d in %(funcName)s()]"
        " - %(message)s"
    ),
)
logging.getLogger("watchdog.observers.inotify_buffer").setLevel(logging.WARNING)

# Load environment variables from .env file if present
load_dotenv()

try:
    # Ensure environment vars are stripped of leading/trailing spaces
    ARCHIVE_DIR = os.getenv("ARCHIVE_DIR").strip()
    UNMATCHED_DIR = os.getenv("UNMATCHED_DIR").strip()

    # Parse and validate SEGMENT_DURATION_SECONDS
    segment_duration_str = os.getenv("SEGMENT_DURATION_SECONDS").strip()
    if not segment_duration_str.isdigit():
        raise ValueError(
            f"SEGMENT_DURATION_SECONDS must be an integer, got '{segment_duration_str}'"
        )
    SEGMENT_DURATION_SECONDS = int(segment_duration_str)

    # Use UTC timezone for consistency
    TZ = pytz.UTC

    logging.debug(
        "Configuration loaded successfully:"
        "ARCHIVE_DIR=`%s`, SEGMENT_DURATION_SECONDS=`%s`, UNMATCHED_DIR=`%s`",
        ARCHIVE_DIR,
        SEGMENT_DURATION_SECONDS,
        UNMATCHED_DIR,
    )
except (ValueError, AttributeError, TypeError) as e:
    logging.error("Failed to load environment variables: `%s`", e)
    sys.exit(1)

# Match ISO 8601 UTC timestamped filenames:
# Expected format: `{STATION_ID}-YYYY-MM-DDTHH:MM:SSZ.mp3`
# Optionally, a conflict counter may be appended: e.g. `-1`, `-2`, etc.
FILENAME_REGEX = re.compile(
    r"^(?P<station_id>.+)-(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})T"
    r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})Z(?:-(?P<counter>\d+))?\.mp3$"
)

RABBITMQ_CLIENT = RabbitMQClient()


def compute_file_hash(file_path, block_size=65536):
    """
    Compute and return the SHA-256 hash of the file at `file_path`.
    """
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while True:
                buf = f.read(block_size)
                if not buf:
                    break
                hasher.update(buf)
    except (OSError, IOError) as e:
        logging.error("Error computing hash for `%s`: %s", file_path, e)
        return None
    return hasher.hexdigest()


@contextmanager
def acquire_lock(lock_file_path):
    """
    Context manager to acquire an exclusive lock on a file.
    """
    # Open (or create) the lock file.
    with open(lock_file_path, "w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


class ArchiveHandler(FileSystemEventHandler):
    """
    Handle file system events in our archive directory.

    This class overrides the `on_moved` method to handle file renames.

    `on_moved` is triggered when a file or directory is moved or
    renamed. We're interested in `.temp` files -> `.mp3`.

    If the file matches the expected format, it is moved to the
    appropriate directory based on its timestamp under the directory
    structure:
        `{ARCHIVE_DIR}/{year}/{month}/{day}` (in UTC).

    If a file is renamed to `.mp3` but *does not* match the expected
    filename format, it is moved to `UNMATCHED_DIR`.
    """

    def on_moved(self, event):
        """
        Triggered when a file or directory is moved or renamed. We're
        interested in `.temp` files -> `.mp3`.

        If the file matches the expected format, move to the appropriate
        directory based on its timestamp under the directory structure:
            `{ARCHIVE_DIR}/{year}/{month}/{day}` (in UTC).

        Parameters:
        - event (FileSystemEvent): The event object containing details
            about the move/rename operation.
        """
        if event.is_directory:
            # Ignore directory moves
            return

        src_ext = os.path.splitext(event.src_path)[1]
        dst_ext = os.path.splitext(event.dest_path)[1]

        if not src_ext == ".temp" and dst_ext == ".mp3":
            logging.error(
                "Unexpected file extension change: `%s` -> `%s`",
                src_ext,
                dst_ext,
            )
            return

        logging.debug("File renamed `%s` -> `%s`", event.src_path, event.dest_path)
        filename = os.path.basename(event.dest_path)

        # Attempt to match the filename to the expected ISO UTC pattern
        match = FILENAME_REGEX.match(filename)
        if not match:
            target_dir = os.path.join(ARCHIVE_DIR, UNMATCHED_DIR)
            logging.warning(
                "Filename `%s` does not match expected format. "
                "Moving to `UNMATCHED_DIR` folder.",
                filename,
            )
        else:
            # Build the directory path based on the timestamp (UTC)
            year = match.group("year")
            month = match.group("month")
            day = match.group("day")
            target_dir = os.path.join(ARCHIVE_DIR, year, month, day)
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError as e:
            logging.error("Failed to create directory `%s`: %s", target_dir, e)
            return

        # Use a lock to ensure atomic conflict-checking and renaming
        lock_file_path = os.path.join(target_dir, ".lock")
        with acquire_lock(lock_file_path):
            # (After `with acquire_lock(lock_file_path)` finishes, the
            # lock is released.)
            new_location = os.path.join(target_dir, filename)
            if os.path.exists(new_location):
                # Conflict! Compute hashes for both files and compare
                try:
                    new_file_hash = compute_file_hash(event.dest_path)
                    existing_file_hash = compute_file_hash(new_location)
                    if new_file_hash is None or existing_file_hash is None:
                        logging.error(
                            "Could not compute file hash for comparison of `%s`",
                            filename,
                        )
                        return
                    if new_file_hash == existing_file_hash:
                        logging.warning(
                            "File `%s` already exists and is identical in "
                            "content. (No conflict). No action taken, "
                            "but this is unexpected.",
                            filename,
                        )
                        return

                    logging.error(
                        "File conflict: path `%s` exists but differs from "
                        "the new file. Adding a counter to the filename...",
                        filename,
                    )
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    temp_location = new_location
                    while os.path.exists(temp_location):
                        temp_location = os.path.join(
                            target_dir, f"{base}-{counter}{ext}"
                        )
                        counter += 1
                    new_location = temp_location
                    logging.info("Renaming conflicting file to `%s`", new_location)
                    # e.g.: `WBOR-2025-02-14T00:40:00Z-1.mp3`
                except (OSError, IOError) as e:
                    logging.error("Error comparing files for `%s`: %s", filename, e)
                    return

            # Now that conflicts are handled, perform atomic move to subdir
            try:
                os.replace(event.dest_path, new_location)
                logging.info("Moved file to `%s`", new_location)
                RABBITMQ_CLIENT.send_message(
                    {
                        "filename": filename,
                        "timestamp": {
                            "year": match.group("year"),
                            "month": match.group("month"),
                            "day": match.group("day"),
                            "hour": match.group("hour"),
                            "minute": match.group("minute"),
                            "second": match.group("second"),
                        },
                    }
                )
            except OSError as e:
                # This is a critical error, as the file has been renamed
                # but not moved. This could lead to data loss if the
                # file is overwritten or left dangling in perpetuity.
                logging.error(
                    "Failed to move file `%s` to `%s`: %s",
                    event.dest_path,
                    new_location,
                    e,
                )
                # Handle by moving the file to the unmatched directory
                unmatched_dir = os.path.join(ARCHIVE_DIR, UNMATCHED_DIR)
                logging.warning(
                    "Moving file to unmatched directory `%s`", unmatched_dir
                )
                os.replace(event.dest_path, os.path.join(unmatched_dir, filename))


def main():
    """
    Entrypoint. Sets up the observer to watch for file renames in the
    archive directory.

    Runs indefinitely until a keyboard interrupt is received.
    """
    event_handler = ArchiveHandler()
    observer = Observer()
    # `recursive=False` to only watch the top-level directory of the archive.
    observer.schedule(event_handler, ARCHIVE_DIR, recursive=False)
    observer.start()

    logging.info("Watching for `.temp` -> `.mp3` renames in `%s`", ARCHIVE_DIR)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping observer from keyboard interrupt")
        observer.stop()
    finally:
        RABBITMQ_CLIENT.close()  # Ensure RabbitMQ connection is closed properly
        logging.debug("RabbitMQ connection closed.")
    observer.join()


if __name__ == "__main__":
    main()
