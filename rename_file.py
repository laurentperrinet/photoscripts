"""
   rename_file.py

A (simple) library to rename files according to a pattern.

https://fr.wikipedia.org/wiki/ISO_8601

"""
DEBUG = True
DEBUG = False
import sys, os, glob


def rename(paths, dryrun=True):
    for path in glob.glob(paths):
        ROOT, filename = os.path.dirname(path), os.path.basename(path)
        newname = filename.replace('Photo', '').replace('Vidéo', '')
#         newname = newname.replace('/', '')
#         newname = newname.replace(':', '')
#         newname = newname.replace('TT', 'T')

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
