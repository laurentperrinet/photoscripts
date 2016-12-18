#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
   rename_exif.py

A (simple) library to organize media files according to their creation date.

The core idea is to rename pictures and movies in a folder by prepending the
date in ISO 8601 format (that is, 2013-12-25 for the 25th of december of 2013).

https://fr.wikipedia.org/wiki/ISO_8601

"""
DEBUG = True
DEBUG = False
# exif_sort[January 2012] / martin gehrke [martin AT teamgehrke.com]
# sorts jpg/jpegs into date folders based on exif data
EXTENSIONS_pict =['jpg','jpeg', 'png']
EXTENSIONS_movie =['mp4', 'mpg', 'mov', '3gp']
EXTENSIONS = []
for EXTENSIONS_ in [EXTENSIONS_pict, EXTENSIONS_movie]:
    [EXTENSIONS.append(ext) for ext in EXTENSIONS_]
    [EXTENSIONS.append(ext.upper()) for ext in EXTENSIONS_]
if DEBUG: print('DEBUG extensions = ', EXTENSIONS)

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
    except Exception as e:
        if DEBUG: print('DEBUG Picture ', fn, ' has no tag, error is: ', e)
        return {}
    #print ret

def get_exif_modification_date(filename, tag='EXIF DateTimeOriginal'):
    from SimpleCV import EXIF
    with open(filename, 'rb') as f:
        UNFORMATTED = EXIF.process_file(f, stop_tag=tag)[tag].printable
    return UNFORMATTED

def format_dateTime(UNFORMATTED):
    if DEBUG: print(UNFORMATTED)
    try:
        DATE, TIME = UNFORMATTED.split()
    except ValueError:
        DATE, TIME = UNFORMATTED.split('T')
    return DATE.replace(':','-') + 'T' + TIME[:8]# + '-'

def get_movie_creation_date(fn):
    for line in os.popen('ffprobe -loglevel quiet -show_format -i ' + fn).readlines():
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

    for PHOTO in glob.glob(paths):
        # 1/ grab the creation date by heuristics
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
                            except: #
                                print('Giving up :-/ ')
                                DATETIME = None
        else:
            print('File ', PHOTO, ' not in the EXTENSION list')
            DATETIME = None
        if DEBUG: print(DATETIME)
        # 2/ prepend the creation date to the file name
        ROOT, FILE = os.path.split(PHOTO)
        if not(DATETIME == None):
            FILE_ = FILE
            if DEBUG: print(FILE_, DATETIME.replace('T', '_').replace('-', '').replace(':', ''))
            FILE_ = FILE_.replace(DATETIME.replace('T', '_').replace('-', '').replace(':', ''), '')
            for sep in ['-', '_', '', '']: # TODO :test the following 3 lines
                FILE_ = FILE_.replace(sep + DATETIME, '') # remove existing occurences of DATETIME
                FILE_ = FILE_.replace(sep + DATETIME[:-1], '') # remove existing occurences of DATETIME
                FILE_ = FILE_.replace(sep + DATETIME[:10], '') # remove existing occurences of DATETIME
                FILE_ = FILE_.replace(sep + DATETIME.replace('-', '')[:8], '') # remove existing occurences of DATETIME
                FILE_ = FILE_.replace(sep + DATETIME[:-1].replace('-', '_'), '')
                FILE_ = FILE_.replace(sep + DATETIME.replace('-', ''), '')
                FILE_ = FILE_.replace('--', '-')
            if DEBUG: print(FILE_.split('.')[0], DATETIME.replace('T', '_').replace('-', '').replace(':', ''))
            if len(FILE_.split('.')[0]) > 0:
                SEP = '_'
            else:
                SEP = ''
            newname = os.path.join(ROOT, "%s%s%s" % (DATETIME, SEP, FILE_))
            for sep in ['-', '_']:
                newname = newname.replace(sep*2, sep)

            N = len(DATETIME)
            if not(DATETIME[:-1] == FILE_[:(N-1)]):
                # in this case, it is different so, we apply the change
                print('renaming ',  PHOTO, ' to ', newname)
                if not(dryrun): os.rename(PHOTO, newname)
            elif False: # TODO (DATETIME.replace('-', '') == FILE[:N_]):
                # HACK : we were before using a version which was missing the dashes
                # now, we have a correct ISO8601
                print('upgrading ',  PHOTO, ' to ', newname)
                if not(dryrun): os.rename(PHOTO, newname)
            else:
                print('already renamed ',  PHOTO, ' with date ', DATETIME[:-1])

if __name__=="__main__":
    args = sys.argv[1:]

    if not len(args):
        print("""
        Usage:
            python rename_exif.py [-d] 'pattern'

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
            sortPhotos(PATH, dryrun=(dryrun=='-d'))
