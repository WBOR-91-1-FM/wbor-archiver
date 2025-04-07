"""
FFprobe utility functions.
"""

import os
import subprocess
import json


def probe(abs_file_path: str) -> dict:
    """
    Get media file information using FFprobe.

    Parameters:
    - abs_file_path (str): Absolute path to the media file.

    Returns:
    - dict: FFprobe output as a dictionary
    """
    if not os.path.exists(abs_file_path):
        raise FileNotFoundError(f"File not found: {abs_file_path}")

    # Run FFprobe
    command = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        abs_file_path,
    ]
    result = subprocess.run(command, capture_output=True, check=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"FFprobe failed with exit code {result.returncode}: {result.stderr}"
        )

    # Parse output
    return json.loads(result.stdout)
