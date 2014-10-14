#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
   rename_exif.py

    A (simple) library to organize media files according to their creation date.

"""
# exif_sort[January 2012] / martin gehrke [martin AT teamgehrke.com]
# sorts jpg/jpegs into date folders based on exif data
EXTENSIONS_pict =['jpg','jpeg', 'png']
EXTENSIONS_movie =['mp4', 'mpg', 'mov']
EXTENSIONS = []
for EXTENSIONS_ in [EXTENSIONS_pict, EXTENSIONS_movie]:
    [EXTENSIONS.append(ext) for ext in EXTENSIONS_]
    [EXTENSIONS.append(ext.upper()) for ext in EXTENSIONS_]
print 'DEBUG extensions = ', EXTENSIONS

from PIL import Image
from PIL.ExifTags import TAGS
import sys, os, glob

import datetime
def modification_date(filename):
    t = os.path.getmtime(filename)
    return str(datetime.datetime.fromtimestamp(t))

def get_exif(fn):
#see <a href="http://www.blog.pythonlibrary.org/2010/03/28/getting-photo-metadata-exif-using-python/">http://www.blog.pythonlibrary.org/2010/03/28/getting-photo-metadata-exif-using-python/</a>
    ret = {}
    i = Image.open(fn)
    try:
        info = i._getexif()
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            ret[decoded] = value
        return ret
    except Exception, e:
        print 'Picture ', fn, ' has no tag, error is: ', e
        return {}
    #print ret

def get_exif_modification_date(filename, tag='EXIF DateTimeOriginal'):
    from SimpleCV import EXIF
    with open(filename, 'rb') as f:
        UNFORMATTED = EXIF.process_file(f, stop_tag=tag)[tag].printable
    return UNFORMATTED

def format_dateTime(UNFORMATTED):
    DATE, TIME = UNFORMATTED.split()
    return DATE[2:].replace('-','').replace(':','') + '-' + TIME.replace(':','') + '-'

def get_movie_creation_date(fn):
    for line in os.popen('ffprobe -loglevel quiet -show_entries stream_tags=creation_time -i ' + fn).readlines():
        #print line
        if line[:18] == 'TAG:creation_time=':
            datetime = line[18:]
            return format_dateTime(datetime)
    return ''

def sortPhotos(paths, dryrun):
#     for root, dirs, files in os.walk(path):
#         if not(root[-9:]=='.@__thumb'):
#             PHOTOS = []
#             for EXTENSION in EXTENSIONS:
#                 PHOTO = glob.glob(os.path.join(root, '*%s' % EXTENSION))
#                 PHOTOS.extend(PHOTO)

    for PHOTO in glob.glob(paths):#PHOTOS:
        # first process movies
        if PHOTO.split('.')[-1].lower() in EXTENSIONS_movie:
            DATETIME = get_movie_creation_date(PHOTO)
            if DATETIME == '':
                DATETIME = format_dateTime(modification_date(PHOTO))
        elif PHOTO.split('.')[-1].lower() in EXTENSIONS_pict: #else: #elif not( get_exif(PHOTO) == {}):
            try: # trying first with SimpleCV
                DATETIME = format_dateTime(get_exif_modification_date(PHOTO))
            except:
#                         print('DEBUG SimpleCV failed ')
                try: # trying with PIL
                    DATETIME = format_dateTime(get_exif(PHOTO)['DateTimeOriginal'])
                except:
                    try: # trying out another tag
                        DATETIME = format_dateTime(get_exif(PHOTO)['DateTime'])
                    except: # yet another one
                        try:
                            DATETIME = format_dateTime(get_exif(PHOTO)['DateTimeModified'])
                        except: # file's modification time 
                            try:
                                DATETIME = format_dateTime(modification_date(PHOTO))
                            except: # Giving up :-)
                                DATETIME = None
        else:
            print('File ', PHOTO, ' not in the EXTENSION list')
            DATETIME = None
        ROOT, FILE = os.path.split(PHOTO)
        newname = os.path.join(ROOT, "%s%s" % (DATETIME, FILE))
#         if dryrun: print('DEBUG: dryrun mode')
        if not(DATETIME == FILE[:14] or DATETIME == None):
            print 'renaming ',  PHOTO, ' to ', newname
            if not(dryrun): os.rename(PHOTO, newname)
        else:
            if not(DATETIME == None): print 'already renamed ',  PHOTO, ' with date ', DATETIME[:-1]

if __name__=="__main__":
    args = sys.argv[1:]

    if not len(args):
        print "Usage: python rename_exif.py [-d] 'pattern'"
    else:
        dryrun = args[0]
        PATHS = args[1:]
        if dryrun != '-d':
            dryrun = ''
            PATHS = args
        if dryrun: print('DEBUG: dryrun mode')
        for PATH in PATHS:
#             print 'Processing path ', PATH
            sortPhotos(PATH, dryrun=='-d')
