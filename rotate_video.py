#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
rotate_video.py

A simple script to rotate videos using ffmpeg.

Supported rotation modes:
  0 = 90° counter-clockwise + vertical flip (default)
  1 = 90° clockwise
  2 = 90° counter-clockwise
  3 = 90° clockwise + vertical flip

Usage:
    python3 rotate_video.py [-c] 'pattern'

    -c: rotate counter-clockwise (default is clockwise)
"""

#     cmd = """
#     ORIGINAL_IFS=$IFS
#     IFS=$'\n'
#     ffmpeg  -i %s -v 0  -vf "transpose=%s"  -qscale 0 -y tmp.mov && mv tmp.mov %s
#     IFS=$ORIGINAL_IFS
#     """ % (PATH, str(int(CCW)), PATH)
#

import sys
from pathlib import Path

def rotate(PATH, CW=False):
    """Rotate a video file using ffmpeg with specified transformation.

    Supported rotation modes:
      0 = 90° counter-clockwise + vertical flip (default)
      1 = 90° clockwise
      2 = 90° counter-clockwise
      3 = 90° clockwise + vertical flip

    Args:
        PATH (str): Path to the video file to rotate.
        CW (bool): If True, rotate counter-clockwise (default is False, i.e.
            clockwise). Use -c flag when running from command line.

    Example:
        python3 rotate_video.py video.mp4          # clockwise rotation
        python3 rotate_video.py -c video.mp4       # counter-clockwise rotation

    Notes:
        - The rotated video is saved as '{original}-tmp.{ext}' then moved
          to replace the original.
        - Uses ffmpeg's transpose filter with appropriate mode value.
    """
    EXT = PATH.split('.')[-1]
#     print 'DEBUG: # of transpose = ', str(1+int(CW))
    cmd = 'ffmpeg  -i "%s" -v 0  -vf "transpose=%s"  -qscale 0 -y "%s-tmp.%s" && mv "%s-tmp.%s" "%s"' % (PATH, str(1 + int(CW)), PATH, EXT, PATH, EXT, PATH)
    print ('DEBUG: cmd = ', cmd)
    try:
        os.system(cmd)
    except Exception as e:
        print ('Command ', cmd, ' failed, error is: ', e)

if __name__=="__main__":
    args = sys.argv[1:]

    if not len(args):
        print("""
        Usage: python rotate_video.py [-c] 'pattern'

        the -c option is to turn video counter-clockwise --- the default is
        clockwise.

        """)
    else:
        CW = args[0]
        PATHS = args[1:]
        if CW != '-c':
            CW = ''
            PATHS = args
        for PATH in PATHS:
            for filename in Path().glob(PATH):
                print ('Processing file ', filename)
                rotate(filename, CW=='-c')
