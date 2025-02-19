"""
This watchdog script monitors the archive directory for `.temp` files being renamed to `.mp3` files, which indicates
that a new recording segment has been completed. It then dynamically moves the file to the appropriate directory based on its
ISO 8601 UTC timestamp (parsed from the filename), and handles any file conflicts by appending a counter to the filename.

If two conflicting file names are detected, the script checks equality of the files. If they are identical (via MD5 hash 
comparison), it deletes the duplicate. If they are different, it appends a counter to the filename until a unique name is found.
Not quite sure how to handle the case where the files are different but have the same name - this is a rare edge case. Perhaps
trigger a manual review in this case? And don't serve the new file until the review is complete.

Thus, the final syntax will be `{STATION_ID}-YYYY-MM-DDTHH:MM:SSZ.mp3`, or `{STATION_ID}-YYYY-MM-DDTHH:MM:SSZ-{counter}.mp3`
if a conflict is detected.

If a file is renamed to `.mp3` but does not match the expected filename format, it is moved to an "unmatched" directory with
the name set in the configuration.

After moving the file, the watchdog script should notify the backend so that it can handle the new segment.
"""

import time
import os
import re
import logging
import pytz
import hashlib
import filecmp
import fcntl
from contextlib import contextmanager
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d in %(funcName)s()] - %(message)s",
)

# Load environment variables from .env file if present
load_dotenv()

try:
    # Ensure environment variables are stripped of leading/trailing spaces
    ARCHIVE_DIR = os.getenv("ARCHIVE_DIR", "/archive").strip()
    UNMATCHED_DIR = "unmatched"

    # Parse and validate SEGMENT_DURATION_SECONDS
    segment_duration_str = os.getenv("SEGMENT_DURATION_SECONDS", "300").strip()
    if not segment_duration_str.isdigit():
        raise ValueError(
            f"SEGMENT_DURATION_SECONDS must be an integer, got '{segment_duration_str}'"
        )
    SEGMENT_DURATION_SECONDS = int(segment_duration_str)

    # Use UTC timezone for consistency
    TZ = pytz.UTC

    logging.info(
        f"Configuration loaded successfully: ARCHIVE_DIR={ARCHIVE_DIR}, SEGMENT_DURATION_SECONDS={SEGMENT_DURATION_SECONDS}, UNMATCHED_DIR={UNMATCHED_DIR}"
    )
except Exception as e:
    logging.error(f"Failed to load environment variables: {e}")
    exit(1)

# Match ISO 8601 UTC timestamped filenames:
# Expected format: `{STATION_ID}-YYYY-MM-DDTHH:MM:SSZ.mp3`
# Optionally, a conflict counter may be appended: e.g. `-1`, `-2`, etc.
FILENAME_REGEX = re.compile(
    r"^(?P<station_id>.+)-(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})Z(?:-(?P<counter>\d+))?\.mp3$"
)


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
    except Exception as e:
        logging.error(f"Error computing hash for {file_path}: {e}")
        return None
    return hasher.hexdigest()


@contextmanager
def acquire_lock(lock_file_path):
    """
    Context manager to acquire an exclusive lock on a file.
    """
    # Open (or create) the lock file.
    with open(lock_file_path, "w") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


class ArchiveHandler(FileSystemEventHandler):
    def on_moved(self, event):
        """
        Triggered when a file or directory is moved or renamed. We're interested in `.temp` files being renamed to `.mp3`.
        If the file matches the expected format, it is moved to the appropriate directory based on its timestamp under
        the directory structure `{ARCHIVE_DIR}/{year}/{month}/{day}` (in UTC).

        Parameters:
        - event (FileSystemEvent): The event object containing details about the move/rename operation.
        """
        if event.is_directory:
            return

        src_ext = os.path.splitext(event.src_path)[1]
        dst_ext = os.path.splitext(event.dest_path)[1]

        # Process only .temp -> .mp3 renames
        if src_ext == ".temp" and dst_ext == ".mp3":
            logging.debug(
                f"File renamed from `{event.src_path}` to `{event.dest_path}`"
            )
            filename = os.path.basename(event.dest_path)

            # Attempt to match the filename to the expected ISO UTC pattern.
            match = FILENAME_REGEX.match(filename)
            if not match:
                # If the filename doesn't match, move it to the UNMATCHED_DIR directory.
                target_dir = os.path.join(ARCHIVE_DIR, UNMATCHED_DIR)
                logging.warning(
                    f"Filename `{filename}` does not match expected format. Moving to `UNMATCHED_DIR` folder."
                )
            else:
                # Build the directory path based on the timestamp (UTC).
                year = match.group("year")
                month = match.group("month")
                day = match.group("day")
                target_dir = os.path.join(ARCHIVE_DIR, year, month, day)

            # Ensure the target directory exists.
            try:
                os.makedirs(target_dir, exist_ok=True)
            except Exception as e:
                logging.error(f"Failed to create directory `{target_dir}`: {e}")
                return

            # Define a lock file within the target directory.
            lock_file_path = os.path.join(target_dir, ".lock")

            # Use the lock to ensure atomic conflict-checking and renaming.
            with acquire_lock(lock_file_path):
                # (After `with acquire_lock(lock_file_path)` finishes, the lock is released.)

                new_location = os.path.join(target_dir, filename)

                if os.path.exists(new_location):
                    try:
                        # Compute hashes for both files.
                        new_file_hash = compute_file_hash(event.dest_path)
                        existing_file_hash = compute_file_hash(new_location)
                        if new_file_hash is None or existing_file_hash is None:
                            logging.error(
                                f"Could not compute file hash for comparison of `{filename}`."
                            )
                            return
                        if new_file_hash == existing_file_hash:
                            logging.info(
                                f"File `{filename}` already exists and is identical in content. No action taken."
                            )
                            return
                        else:
                            logging.error(
                                f"File conflict: `{filename}` exists and differs from the new file."
                            )
                            # Append a counter suffix until a unique name is found.
                            base, ext = os.path.splitext(filename)
                            counter = 1
                            temp_location = new_location
                            while os.path.exists(temp_location):
                                temp_location = os.path.join(
                                    target_dir, f"{base}-{counter}{ext}"
                                )
                                counter += 1
                            new_location = temp_location
                            logging.info(
                                f"Renaming conflicting file to `{new_location}`."
                            )
                            # E.g.: `WBOR-2025-02-14T00:40:00Z-1.mp3`
                    except Exception as e:
                        logging.error(f"Error comparing files for `{filename}`: {e}")
                        return

                # Use os.replace for atomic move.
                try:
                    os.replace(event.dest_path, new_location)
                    logging.info(f"Moved file to `{new_location}`")
                    # At this point, the watchdog should notify the backend
                except Exception as e:
                    logging.error(
                        f"Failed to move file `{event.dest_path}` to `{new_location}`: {e}"
                    )


def main():
    event_handler = ArchiveHandler()
    observer = Observer()
    observer.schedule(event_handler, ARCHIVE_DIR, recursive=False)
    observer.start()

    logging.info(f"Watching for `.temp` -> `.mp3` renames in `{ARCHIVE_DIR}` ...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping observer from keyboard interrupt")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
