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
    --clean        : remove existing date prefixes instead of adding them
    --compact      : use compact date format (YYYY-MM-DDThhmmss)
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

import os
from PIL import Image
from PIL.ExifTags import TAGS
import sys
import glob
import subprocess

import datetime
import re


def modification_date(filename):
    """Return the file's modification date as an ISO 8601 string."""
    t = os.path.getmtime(filename)
    return str(datetime.datetime.fromtimestamp(t))


def get_exif(fn):
    """Extract EXIF metadata from an image file."""
    ret = {}
    try:
        i = Image.open(fn)
        info = i._getexif()
        if info:
            for tag, value in info.items():
                decoded = TAGS.get(tag, tag)
                ret[decoded] = value
        return ret
    except Exception:
        return {}


def get_exif_modification_date(filename, tag='EXIF DateTimeOriginal'):
    """Read a specific EXIF tag from a file using SimpleCV."""
    try:
        from SimpleCV import EXIF
        with open(filename, 'rb') as f:
            UNFORMATTED = EXIF.process_file(f, stop_tag=tag)[tag].printable
        return UNFORMATTED
    except Exception:
        return ''


def format_dateTime(UNFORMATTED):
    """Format an unformatted date-time string into ISO 8601 format."""
    if not UNFORMATTED:
        return ''
    if 'T' in UNFORMATTED:
        try:
            DATE, TIME = UNFORMATTED.split('T', 1)
        except ValueError:
            DATE, TIME = UNFORMATTED, ''
    else:
        parts = UNFORMATTED.split()
        if len(parts) >= 6:
            DATE = '-'.join(parts[:3])
            TIME = ':'.join(parts[3:6])
        else:
            DATE, TIME = UNFORMATTED.split(maxsplit=1) if len(parts) == 2 else (UNFORMATTED, '')

    if TIME:
        if '.' in TIME:
            TIME = TIME.split('.')[0]
        if 'Z' in TIME:
            TIME = TIME.split('Z')[0]
        if '+' in TIME or (len(TIME) > 1 and TIME[0] == '-' and TIME[1] in '+-'):
            for i, c in enumerate(TIME):
                if c in '+-' and i > 0:
                    TIME = TIME[:i]
                    break

    return DATE.replace(':', '-') + ('T' + TIME if TIME else '')


def _extract_date_from_exif(fn):
    """Extract date from EXIF data using PIL, trying tags in priority order."""
    exif = get_exif(fn)
    for tag in ['DateTimeOriginal', 'DateTime', 'DateTimeModified']:
        try:
            if tag in exif:
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
        return None


def _clean_filename_date(filename, date_str, keep_compact=False):
    """Remove existing date occurrences from filename stem.

    Removes any date-like prefix (ISO 8601, compact, etc.) regardless of whether
    it matches the extracted date_str.
    """
    import re

    # Generic patterns for date/time components
    date_pattern = r'(\d{4}-\d{2}-\d{2}|\d{8})'
    sep_pattern = r'[T_-]?'
    time_pattern = r'(\d{2}[:_]?\d{2}[:_]?\d{2})'
    full_date_pattern = f"^{date_pattern}{sep_pattern}{time_pattern}"

    result = filename

    # We only care about the date_str if we are in keep_compact mode
    # and we want to preserve a compact date that matches the actual date.
    # However, based on user feedback, the priority is to remove ANY existing date
    # and replace it with the correct one.

    # If keep_compact is True, the user wants to preserve a compact date.
    # But only if it's a valid date. To avoid the "double date" issue when dates differ,
    # we should first strip all date-like prefixes, and then if keep_compact is true,
    # we will let the calling function handle the prepending.
    # Actually, if keep_compact is True, the calling function prepends the compact date.
    # So we should just clean everything.

    while True:
        original = result
        # 1. Remove full date-time patterns (e.g., 2026-09-01T22:10:48 or 20260901T221048)
        result = re.sub(full_date_pattern, '', result)
        # 2. Remove date-only patterns (e.g., 2026-09-01 or 20260901)
        result = re.sub(r'^' + date_pattern, '', result)
        result = re.sub(r'[-_]' + date_pattern, '', result)
        # 3. Remove time-only patterns (e.g., 22:10:48 or 221048)
        result = re.sub(r'^' + time_pattern, '', result)
        result = re.sub(r'[-_]' + time_pattern, '', result)

        result = result.strip('-_')
        if result == original:
            break

    return result


def get_movie_creation_date(fn):
    """Extract the creation date from a movie file using ffprobe.

    Tries the Apple-specific 'com.apple.quicktime.creationdate' tag first,
    as it usually contains the actual capture date, then falls back to
    the standard 'creation_time' tag.
    """
    fn_str = str(fn)
    tags = ['com.apple.quicktime.creationdate', 'creation_time']

    for tag in tags:
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-show_entries', f'format_tags={tag}',
                 '-of', 'default=noprint_wrappers=1:nokey=1', '-i', fn_str],
                capture_output=True, text=True
            )
            date_str = result.stdout.strip()
            if date_str:
                return format_dateTime(date_str)
        except Exception:
            continue
    return ''

def sortPhotos(paths, dryrun, verbose=False, clean_mode=False, compact_mode=False):
    """Process files matching the given paths and rename them with their creation date."""
    if verbose:
        global DEBUG
        DEBUG = True
    for PHOTO in glob.glob(paths):
        DATETIME = _get_creation_date(PHOTO)
        if DATETIME is None:
            continue

        PHOTO_PATH = Path(PHOTO)
        stem = PHOTO_PATH.stem
        suffix = PHOTO_PATH.suffix

        clean_stem = _clean_filename_date(stem, DATETIME, keep_compact=compact_mode)

        if clean_mode:
            new_filename = clean_stem + suffix
        else:
            if compact_mode:
                date_part = DATETIME[:10]
                time_part = DATETIME[11:].replace(':', '')
                fmt_date = f"{date_part}T{time_part}"
            else:
                fmt_date = DATETIME

            sep = '_' if clean_stem else ''
            new_filename = f"{fmt_date}{sep}{clean_stem}{suffix}"

        for s in ['-', '_']:
            new_filename = new_filename.replace(s * 2, s)
        new_filename = new_filename.replace('-_', '_').replace('_-', '_')

        newname = str(PHOTO_PATH.parent / new_filename)

        if DEBUG:
            print(f"📅 {DATETIME} | 🔄 {PHOTO_PATH.name} ➔ {new_filename}")

        if not dryrun:
            PHOTO_PATH.rename(newname)


def test_pairs_from_tsv(tsv_path='test_pairs.tsv'):
    """Test _clean_filename_date against all pairs in a TSV file."""
    import os
    passed = 0
    failed = 0
    try:
        with open(tsv_path, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"❌ {tsv_path} not found")
        return False

    if not lines:
        print("❌ TSV file is empty")
        return False
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
        help='dry-run mode: show what would be renamed without actually renaming'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        default=False,
        help='print debug information'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        default=False,
        help='run TSV test suite from test_pairs.tsv and exit'
    )
    parser.add_argument(
        '--clean',
        action='store_true',
        default=False,
        help='remove existing date prefixes instead of prepending the date'
    )
    parser.add_argument(
        '--compact',
        action='store_true',
        default=True,
        help='use compact date format (YYYY-MM-DDThhmmss)'
    )
    parser.add_argument(
        'paths',
        metavar='PATH',
        nargs='*',
        help='file patterns or folder paths to process'
    )
    args = parser.parse_args()
    tsv_file = 'test_pairs.tsv'
    run_tsv_test = args.test or (not args.paths and os.path.exists(tsv_file))
    if run_tsv_test:
        if not os.path.exists(tsv_file):
            print(f"⚠️  {tsv_file} not found")
            exit(1)
        print(f"Running tests from {tsv_file}...")
        success = test_pairs_from_tsv(tsv_file)
        if not success:
            exit(1)
        exit(0)
    for PATH in args.paths:
        sortPhotos(PATH, dryrun=(args.dry_run), verbose=args.verbose, clean_mode=args.clean, compact_mode=args.compact)
