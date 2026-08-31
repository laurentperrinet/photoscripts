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
import sys, os, glob

import datetime


def modification_date(filename):
    """Return the file's modification date as an ISO 8601 string.

    Args:
        filename (str): Path to the file.

    Returns:
        str: Modification date as returned by datetime.fromtimestamp.
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
    try:
        DATE, TIME = UNFORMATTED.split()
    except ValueError:
        DATE, TIME = UNFORMATTED.split('T')
    return DATE.replace(':', '-') + 'T' + TIME[:8].replace(':', '')


def get_movie_creation_date(fn):
    """Extract the creation date from a movie file using ffprobe.

    Looks for TAG:creation_time in the ffprobe output and formats it.

    Args:
        fn (str): Path to the movie file.

    Returns:
        str: Date in ISO 8601 format, or empty string if not found.
    """
    for line in os.popen('ffprobe -loglevel quiet -show_format -i ' + fn).readlines():
        if line[:18] == 'TAG:creation_time=':
            datetime_str = line[18:]
            return format_dateTime(datetime_str)
    return ''


def sortPhotos(paths, dryrun, verbose=False):
    """Process files matching the given paths and rename them with their creation date.

    For each file, extracts the creation date using EXIF data (pictures) or
    ffprobe (movies), then prepends the date to the filename in ISO 8601 format.

    Handles fallback chains when primary date sources are unavailable, and
    cleans existing date strings from filenames to avoid duplicates.

    Args:
        paths (str or list): Single file pattern or list of file paths/folders.
        dryrun (bool): If True, only show what would be renamed without actually
            renaming files.
        verbose (bool): If True, print debug information. Defaults to False.
    """
    if verbose:
        global DEBUG
        DEBUG = True
    for PHOTO in glob.glob(paths):
        # 1/ grab the creation date by heuristics
        # first process movies
        if PHOTO.split('.')[-1].lower() in EXTENSIONS_movie:
            DATETIME = get_movie_creation_date(PHOTO)
            if DATETIME == '':
                DATETIME = format_dateTime(modification_date(PHOTO))
        elif PHOTO.split('.')[-1].lower() in EXTENSIONS_pict:
            try:  # trying first with SimpleCV
                DATETIME = format_dateTime(get_exif_modification_date(PHOTO))
            except Exception:
                try:  # trying with PIL
                    exif = get_exif(PHOTO)
                    DATETIME = format_dateTime(exif['DateTimeOriginal'])
                except Exception:
                    try:  # trying out another tag
                        DATETIME = format_dateTime(exif['DateTime'])
                    except Exception:
                        try:  # yet another one
                            DATETIME = format_dateTime(exif['DateTimeModified'])
                        except Exception:  # file's modification time
                            try:
                                DATETIME = format_dateTime(modification_date(PHOTO))
                            except Exception:
                                print('Giving up :-/ ')
                                DATETIME = None
        else:
            print('File ', PHOTO, ' not in the EXTENSION list')
            DATETIME = None

        if DEBUG:
            print(DATETIME)

        # 2/ prepend the creation date to the file name
        ROOT, FILE = os.path.split(PHOTO)
        if not (DATETIME is None):
            FILE_ = FILE
            if DEBUG:
                print(FILE_, DATETIME.replace('T', '_').replace('-', ''))

            # Remove any existing occurrence of the date from the filename
            FILE_ = FILE_.replace(DATETIME.replace('T', '-'), '')
            FILE_ = FILE_.replace(DATETIME.replace('T', '_').replace('-', ''), '')
            FILE_ = FILE_.replace(DATETIME.replace('T', '_').replace('-', ''), '')

            for sep in ['-', '_', '', '']:
                FILE_ = FILE_.replace(sep + DATETIME, '')  # remove existing occurrences of DATETIME
                FILE_ = FILE_.replace(sep + DATETIME[:-1], '')  # remove existing occurrences of DATETIME
                FILE_ = FILE_.replace(sep + DATETIME[:10], '')  # remove existing occurrences of DATETIME
                FILE_ = FILE_.replace(sep + DATETIME.replace('-', '')[:8], '')  # remove existing occurrences of DATETIME
                FILE_ = FILE_.replace(sep + DATETIME[:-1].replace('-', '_'), '')
                FILE_ = FILE_.replace(sep + DATETIME.replace('-', ''), '')
                FILE_ = FILE_.replace('--', '-')

            if DEBUG:
                print(FILE_.split('.')[0], DATETIME.replace('T', '_').replace('-', ''))

            if len(FILE_.split('.')[0]) > 0:
                SEP = '_'
            else:
                SEP = ''

            newname = os.path.join(ROOT, "%s%s%s" % (DATETIME, SEP, FILE_))

            # Normalize double separators
            for sep in ['-', '_']:
                newname = newname.replace(sep*2, sep)
            newname = newname.replace('-_', '_')
            newname = newname.replace('_-', '_')

            N = len(DATETIME)
            if not (DATETIME[:-1] == FILE_[:(N-1)]):
                # in this case, it is different so, we apply the change
                print('renaming ', PHOTO, ' to ', newname)
                if not dryrun:
                    os.rename(PHOTO, newname)

                ext = PHOTO.split('.')[-1]
                for ext_meta in EXTENSIONS_meta:
                    if os.path.isfile(PHOTO.replace(ext, ext_meta)):
                        # print('meta  ',  ext, ext_meta)
                        print('meta renaming ', PHOTO.replace(ext, ext_meta), ' to ', newname.replace(ext, ext_meta))
                        if not dryrun:
                            os.rename(PHOTO.replace(ext, ext_meta), newname.replace(ext, ext_meta))

            elif False:  # TODO (DATETIME.replace('-', '') == FILE[:N_]):
                # HACK: we were before using a version which was missing the dashes
                # now, we have a correct ISO8601
                print('upgrading ', PHOTO, ' to ', newname)
                if not dryrun:
                    os.rename(PHOTO, newname)
            else:
                print('already renamed ', PHOTO, ' with date ', DATETIME[:-1])


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

    for PATH in args.paths:
        sortPhotos(PATH, dryrun=(args.dry_run), verbose=args.verbose)