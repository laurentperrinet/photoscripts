"""
   rename_file.py

A (simple) library to rename files according to a pattern.

https://fr.wikipedia.org/wiki/ISO_8601

"""
DEBUG = True
DEBUG = False
import sys, os, glob


def rename(paths, dryrun=True):
    for filename in glob.glob(paths):
        try:
            # 2017-07-30_1238340573
            # 2017-07-30_T12:38:34_0573Z
            newname = filename[:14] + 'T' + filename[14:16] + ':' + filename[16:18] + ':' + filename[18:20] + 'Z_' + filename[20:]
            print('renaming ', filename, ' to ', newname)
            if not(dryrun): os.rename(filename, newname)
        except Exception as e:
            print('renaming ', filename, ' failed with', e)

if __name__=="__main__":
    args = sys.argv[1:]

    if not len(args):
        print("""
        Usage:
            python3 rename_file.py [-d] 'pattern'

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
