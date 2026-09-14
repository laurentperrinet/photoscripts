"""
rename_file.py

A simple library to rename files according to a pattern.

Supported patterns:
  - Replace "Photo" and "Vidéo" prefixes in filenames
  - Format dates in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)

Usage:
    python3 rename_file.py [-d] 'pattern'

    -d: dry-run mode (show what would be renamed without actually renaming)

Files are processed by:
  1. Removing "Photo" and "Vidéo" prefixes
  2. Prepending creation date in ISO 8601 format if recognized
  3. Outputting the new filename for verification
"""
DEBUG = True
DEBUG = False
import sys, os, glob


def rename(paths, dryrun=True):
    """Rename files by removing 'Photo'/'Vidéo' prefixes and prepending creation date.

    Files are processed by:
    1. Removing 'Photo' and 'Vidéo' prefixes from the filename
    2. Prepending creation date in ISO 8601 format (YYYY-MM-DDTHH:MM:SS) if recognized
       from the existing filename pattern (e.g., 2017-07-30_1238340573)
    3. Outputting the rename operation for verification

    Args:
        paths (str): File pattern or path to process (supports glob patterns).
        dryrun (bool): If True, only show what would be renamed without actually
            renaming files. Defaults to True.

    Example:
        python3 rename_file.py -d '*.jpg'
        python3 rename_file.py 'Photo*2023*'

    Returns:
        None: Prints rename operations to stdout.
    """
    for path in glob.glob(paths):
        ROOT, filename = os.path.dirname(path), os.path.basename(path)
        newname = filename.replace('Photo', '').replace('Vidéo', '')

        try:
            # 2017-07-30_1238340573
            # 2017-07-30_T12:38:34_0573Z
            if not 'Z_' in newname:
                newname = newname[:11] + 'T' + newname[11:17] + 'Z_' + newname[17:]
#             if len(filename.split('Z_'))>2:
#                 A, B, C = filename.split('Z_')
#                 filename = A + B + 'Z_' + C
            print('renaming \033[0;32m' + os.path.join(ROOT, filename) + '\033[00m to \033[0;32m' + os.path.join(ROOT, newname) + '\033[00m')
            if not(dryrun): os.rename(os.path.join(ROOT, filename), os.path.join(ROOT, newname))
        except Exception as e:
            print('renaming ', filename, ' failed with', e)

if __name__=="__main__":
    args = sys.argv[1:]

    if not len(args):
        print("""
        Usage:
            python rename_file.py [-d] 'pattern'

            -d: dry-run mode
            """)
    else:
        dryrun = args[0]
        PATHS = args[1:]
        if dryrun != '-d':
            dryrun = ''
            PATHS = args
        if DEBUG:
            if (dryrun== '-d'): print('DEBUG: dryrun mode')
        for PATH in PATHS:
#             print 'Processing path ', PATH
            rename(PATH, dryrun=(dryrun=='-d'))
