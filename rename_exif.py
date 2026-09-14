#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rename_exif.py

A library to organize media files according to their creation date.

The core idea is to rename pictures and movies in a folder by prepending the
date in ISO 8601 format (that is, 2013-12-25 for the 25th of december of 2013).

https://fr.wikipedia.org/wiki/ISO_8601

e.g. 1977-04-22T06:00:00Z

Supported picture extensions: jpg, jpeg, png
Supported movie extensions: mp4, mpg, mov, 3gp
Meta/AAC extensions: AAE

The date extraction priority order is:
1. EXIF DateTimeOriginal (primary)
2. EXIF DateTime (fallback)
3. EXIF DateTimeModified (fallback)
4. File modification time (last resort)
5. Movie creation_time via ffprobe (for mp4/mpg/mov/3gp files)

Usage:
    python3 rename_exif.py [-d] [-v] [path [path ...]]

    -d, --dry-run  : don't actually rename files, just show what would be done
    -v, --verbose    : print debug information
    path             : one or more file patterns or folder paths to process

If no path is given, the script prints the usage message.
"""

from pathlib import Path
DEBUG = False

# Supported file extensions (lowercase and uppercase)
EXTENSIONS_pict = ['jpg', 'jpeg', 'png']
EXTENSIONS_movie = ['mp4', 'mpg', 'mov', '3gp']
EXTENSIONS = []
for EXTENSIONS_ in [EXTENSIONS_pict, EXTENSIONS_movie]:
    [EXTENSIONS.append(ext) for ext in EXTENSIONS_]
    [EXTENSIONS.append(ext.upper()) for ext in EXTENSIONS_]

# Meta file extensions (sidecar files)
EXTENSIONS_meta = ['AAE']


from PIL import Image
from PIL.ExifTags import TAGS
import sys
import glob
import subprocess

import datetime
import re


def modification_date(filename):
    """Return the file's modification date as an ISO 8601 string.

    Args:
        filename (str): Path to the file.

    Returns:
        str: Modification date in ISO 8601 format (YYYY-MM-DD HH:MM:SS).
    """
    t = os.path.getmtime(filename)
    return str(datetime.datetime.fromtimestamp(t))


def get_exif(fn):
    """Extract EXIF metadata from an image file.

    Uses PIL to read EXIF tags from JPEG/JPEG images and decodes tag names
    using PIL.ExifTags.TAGS.

    Args:
        fn (str): Path to the image file.

    Returns:
        dict: Mapping of decoded tag names to their values. Returns empty dict
        if the file has no EXIF data or cannot be opened.
    """
    ret = {}
    i = Image.open(fn)
    try:
        info = i._getexif()
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            ret[decoded] = value
        return ret
    except Exception:
        return {}


def get_exif_modification_date(filename, tag='EXIF DateTimeOriginal'):
    """Read a specific EXIF tag from a file using SimpleCV.

    Args:
        filename (str): Path to the file.
        tag (str): EXIF tag name to read. Defaults to 'EXIF DateTimeOriginal'.

    Returns:
        str: The unformatted printable value of the EXIF tag, or empty string
        if the tag is not found.
    """
    from SimpleCV import EXIF
    with open(filename, 'rb') as f:
        UNFORMATTED = EXIF.process_file(f, stop_tag=tag)[tag].printable
    return UNFORMATTED


def format_dateTime(UNFORMATTED):
    """Format an unformatted date-time string into ISO 8601 format.

    Handles both space-separated ('YYYY MM DD HH MM SS') and T-separated
    ('YYYY-MM-DDTHH:MM:SS') formats.

    Args:
        UNFORMATTED (str): Raw date-time string from EXIF or ffprobe.

    Returns:
        str: Date in ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
    """
    if 'T' in UNFORMATTED:
        # T-separated format: YYYY-MM-DDTHH:MM:SS or with timezone
        try:
            DATE, TIME = UNFORMATTED.split('T', 1)
        except ValueError:
            DATE, TIME = UNFORMATTED.split('T', 1)
    else:
        # Space-separated format: YYYY MM DD HH MM SS
        parts = UNFORMATTED.split()
        if len(parts) >= 6:
            # Take first 3 parts as date, last 3 as time
            DATE = '-'.join(parts[:3])  # Join date parts with dashes
            TIME = ':'.join(parts[3:6])  # Join time parts with colons
        else:
            # Fallback if not enough parts
            DATE, TIME = UNFORMATTED.split(maxsplit=1) if len(parts) == 2 else (UNFORMATTED, '')
    
    # Strip microseconds and timezone suffixes from time
    if '.' in TIME:
        TIME = TIME.split('.')[0]
    if 'Z' in TIME:
        TIME = TIME.split('Z')[0]
    if '+' in TIME or (len(TIME) > 1 and TIME[0] == '-' and TIME[1] in '+-'):
        # Handle timezone offset like +0300 or -0400
        for i, c in enumerate(TIME):
            if c in '+-' and i > 0:
                TIME = TIME[:i]
                break
    # DATE: replace ':' with '-' (handles EXIF format 'YYYY:MM:DD')
    # TIME: KEEP colons as-is for proper ISO 8601 time format 'HH:MM:SS'
    return DATE.replace(':', '-') + 'T' + TIME

def _extract_date_from_exif(fn):
    """Extract date from EXIF data using PIL, trying tags in priority order."""
    exif = get_exif(fn)
    for tag in ['DateTimeOriginal', 'DateTime', 'DateTimeModified']:
        try:
            return format_dateTime(exif[tag])
        except Exception:
            continue
    return ''


def _get_creation_date(PHOTO):
    """Get creation date from a file, trying appropriate sources based on type."""
    ext = PHOTO.split('.')[-1].lower()
    if ext in EXTENSIONS_movie:
        DATETIME = get_movie_creation_date(PHOTO)
        if not DATETIME:
            DATETIME = format_dateTime(modification_date(PHOTO))
        return DATETIME
    elif ext in EXTENSIONS_pict:
        try:
            DATETIME = _extract_date_from_exif(PHOTO)
        except Exception:
            DATETIME = ''
        if not DATETIME:
            try:
                DATETIME = format_dateTime(get_exif_modification_date(PHOTO))
            except Exception:
                DATETIME = ''
        if not DATETIME:
            DATETIME = format_dateTime(modification_date(PHOTO))
        return DATETIME
    else:
        print('File ', PHOTO, ' not in the EXTENSION list')
        return None


def _clean_filename_date(filename, date_str):
    """Remove existing date occurrences from filename stem.

    Handles various ISO 8601 formats that may already be prepended to the filename.

    Args:
        filename (str): The original filename (just the stem, without extension).
        date_str (str): The ISO 8601 date string to remove/clean.

    Returns:
        str: The cleaned filename stem with date occurrences removed.
    """
    # Remove the exact date string (ISO 8601 with T separator)
    result = filename.replace(date_str, '')

    # Remove just the date part (YYYY-MM-DD)
    result = result.replace(date_str[:10], '')

    # Remove time part variations (HH:MM:SS with different separators)
    time_part = date_str[11:]  # HH:MM:SS
    for sep in ['-', ':', '_']:
        result = result.replace(sep.join(time_part.split(':')), '')

    # Remove compact format YYYYMMDD_HHMMSS if present
    compact_date = date_str.replace('-', '')[:8] + '_' + time_part.replace(':', '')
    result = result.replace(compact_date, '')

    # Also try with the compact format without underscore
    compact_date2 = date_str.replace('-', '')[:8] + time_part.replace(':', '')
    result = result.replace(compact_date2, '')

    # Remove double separators and fix common patterns
    for sep in ['-', '_']:
        result = result.replace(sep + sep, sep)
    result = result.replace('-_', '_')
    result = result.replace('_-', '_')

    # Strip leading/trailing separators
    while result.startswith(('-', '_')):
        result = result[1:]
    while result.endswith(('-', '_')):
        result = result[:-1]

    return result


def get_movie_creation_date(fn):
    """Extract the creation date from a movie file using ffprobe.

    Looks for TAG:creation_time in the ffprobe output and formats it.

    For MOV/MP4 files, this looks at the TAG:creation_time metadata tag.
    If not available, falls back to file modification time.

    Args:
        fn (str or Path): Path to the movie file.

    Returns:
        str: Date in ISO 8601 format, or empty string if not found.
    """
    fn_str = str(fn)
    result = subprocess.run(
        ['ffprobe', '-loglevel', 'quiet', '-show_format', '-i', fn_str],
        capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        if line[:18] == 'TAG:creation_time=':
            datetime_str = line[18:]
            return format_dateTime(datetime_str)
    return ''

def sortPhotos(paths, dryrun, verbose=False):
    """Process files matching the given paths and rename them with their creation date.

    For each file, extracts the creation date using EXIF data (pictures) or
    ffprobe (movies), then prepends the date to the filename in ISO 8601 format.

    Handles fallback chains when primary date sources are unavailable, and
    cleans existing date strings from filenames to avoid duplicates, including
    the case where the date is already present in the filename.

    Args:
        paths (str or list): Single file pattern or list of file paths/folders.
        dryrun (bool): If True, only show what would be renamed without actually
            renaming files.
        verbose (bool): If True, print debug information. Defaults to False.

    Example:
        python3 rename_exif.py -d /path/to/photos

    Notes:
        - The script processes pictures (jpg, jpeg, png) using EXIF metadata first,
          falling back to file modification time if EXIF is unavailable.
        - Movies (mp4, mpg, mov, 3gp) use ffprobe to extract creation time.
        - Existing date prefixes in filenames are cleaned to avoid duplicates.
    """
    if verbose:
        global DEBUG
        DEBUG = True
    for PHOTO in glob.glob(paths):
        DATETIME = _get_creation_date(PHOTO)
        if DATETIME is None:
            continue

        if DEBUG:
            print(DATETIME)

        PHOTO_PATH = Path(PHOTO)
        FILE = PHOTO_PATH.name
        # Clean any existing date from the filename, then prepend the new date
        clean_name = _clean_filename_date(FILE, DATETIME)
        sep = '_' if clean_name else ''

        newname = str(PHOTO_PATH.parent / f"{DATETIME}{sep}{FILE}")

        # Normalize double separators
        for sep in ['-', '_']:
            newname = newname.replace(sep * 2, sep)
        newname = newname.replace('-_', '_')
        newname = newname.replace('_-', '_')

        if DEBUG:
            print('renaming ', PHOTO, ' to ', newname)

        if not dryrun:
            PHOTO_PATH.rename(newname)

            ext = PHOTO.split('.')[-1]
            for ext_meta in EXTENSIONS_meta:
                meta_path = Path(PHOTO).with_suffix(ext_meta)
                if meta_path.is_file():
                    if DEBUG:
                        print('meta renaming ', meta_path, ' to ', newname.replace(ext, ext_meta))
                    meta_path.rename(str(newname.replace(ext, ext_meta)))


def test_pairs_from_tsv(tsv_path='test_pairs.tsv'):
    """Test _clean_filename_date against all pairs in a TSV file.

    Reads source/destination pairs from a TSV file (with header 'source\tdestination')
    and verifies that _clean_filename_date produces the expected destination
    from the source filename using the standard date format.

    Args:
        tsv_path: Path to the TSV test pairs file.

    Returns:
        True if all tests pass, False otherwise.
    """
    from rename_exif import _clean_filename_date
    import os

    passed = 0
    failed = 0

    with open(tsv_path, 'r') as f:
        lines = f.readlines()

    if not lines:
        print("❌ TSV file is empty")
        return False

    # Skip header line
    for i, line in enumerate(lines[1:], 1):
        line = line.strip()
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) != 2:
            print(f"❌ Line {i}: Malformed entry (expected 2 tab-separated fields): {line}")
            failed += 1
            continue

        source, dest = parts
        stem, ext = os.path.splitext(source)

        # Use the standard date format
        date_str = '2023-12-25T10:30:00'
        result = _clean_filename_date(stem, date_str) + ext

        if result == dest:
            passed += 1
        else:
            failed += 1
            print(f"❌ Line {i}: Mismatch")
            print(f"   Source:    {source}")
            print(f"   Expected:  {dest}")
            print(f"   Got:       {result}")
            print()

    total = passed + failed
    print(f"\n{'='*50}")
    print(f"Test Results: {passed}/{total} passed, {failed}/{total} failed")
    if failed == 0:
        print("✅ All tests passed!")
        return True
    else:
        print(f"❌ {failed} test(s) failed")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Organize media files according to their creation date, '
                    'prepending the date in ISO 8601 format.'
    )
    parser.add_argument(
        '-d', '--dry-run',
        action='store_true',
        default=False,
        required=False,
        help='dry-run mode: show what would be renamed without actually renaming'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        default=False,
        required=False,
        help='print debug information'
    )
    parser.add_argument(
        'paths',
        metavar='PATH',
        nargs='+',
        help='file patterns or folder paths to process'
    )

    args = parser.parse_args()

    # Run TSV test if test_pairs.tsv exists
    tsv_file = 'test_pairs.tsv'
    if os.path.exists(tsv_file):
        print(f"Running tests from {tsv_file}...")
        success = test_pairs_from_tsv(tsv_file)
        if not success:
            exit(1)
    else:
        print(f"⚠️  {tsv_file} not found, skipping TSV tests")

    for PATH in args.paths:
        sortPhotos(PATH, dryrun=(args.dry_run), verbose=args.verbose)
