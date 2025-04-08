"""
Generate the SHA-256 hash of a file.
"""

import hashlib
import os
from typing import Optional


def hash_file(abs_file_path: str) -> Optional[str]:
    """
    Generate the SHA-256 hash of a file.

    Parameters:
    - abs_file_path (str): Absolute path to the file.

    Returns:
    - Optional[str]: SHA-256 hash of the file, or None if the file does not exist.

    Note:
    - The hash is computed in chunks to avoid loading the entire file into memory
    - The file is read in binary mode (`rb`)

    Example:
    >>> hash_file("example.txt")
    'c3fcd3d76192e4007dfb496cca67e13b'
    """

    if not os.path.exists(abs_file_path):
        return None

    sha256 = hashlib.sha256()
    # `rb` mode is used to read the file in binary mode
    with open(abs_file_path, "rb") as f:
        while chunk := f.read(4096):
            sha256.update(chunk)

    # Return the hexadecimal representation of the hash
    return sha256.hexdigest()
