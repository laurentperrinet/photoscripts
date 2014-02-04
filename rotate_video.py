#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
   rotate_video.py

    A (simple) library to rotate movies.

"""



import sys, os, glob

def rotate(PATH, CCW=='-c'):

    cmd = """
    ORIGINAL_IFS=$IFS
    IFS=$'\n'
    ffmpeg  -i %s -v 0  -vf "transpose=%s"  -qscale 0 -y tmp.mov && mv tmp.mov %s
    IFS=$ORIGINAL_IFS
    """ % (PATH, str(int(CCW)), PATH)
    try:
        os.system(cmd)
    except Exception, e:
        print 'Command ', cmd, ' failed, error is: ', e

ORIGINAL_IFS=$IFS
IFS=$'\n'
ffmpeg  -i $1 -v 0  -vf "transpose=$2"  -qscale 0 -y tmp.mov && mv tmp.mov $1
IFS=$ORIGINAL_IFS

if __name__=="__main__":
    args = sys.argv[1:]

    if not len(args):
        print "Usage: python rotate_video.py [-c] 'pattern'"
    else:
        CCW = args[0]
        PATHS = args[1:]
        if CCW != '-c':
            CCW = ''
            PATHS = args
        for PATH in PATHS:
            print 'Processing file ', PATH
            rotate(PATH, CCW=='-c')