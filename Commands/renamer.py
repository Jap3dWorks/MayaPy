import argparse

import re

import os

import shutil

import logging
logging.basicConfig()
logger = logging.getLogger('renamer')
logger.setLevel(logging.DEBUG)



def main():
    """
    This is the function that gets run by default when this module is executed.
    It is common convention to call this first function 'main' but it can be called anything you like
    """
    parser = argparse.ArgumentParser(description='this is a simple batch renaming tool to rename sequence of files',
                                     usage='to replace all files with hello with goodbye: python renamer.py hello goodbye')
    # add positional arguments they must be given
    parser.add_argument('inString', help= 'the word o regex pattern to replace')
    parser.add_argument('outString', help= 'he word or pattern regex to replace it with')

    # action='store_true' -> default false, if provided true
    parser.add_argument('-d', '--duplicate', help='should we dupliate or write over original files', action='store_true')
    parser.add_argument('-r','--regex', help='wheter the inputs will be using regex or not', action='store_true')

    # optional argument
    parser.add_argument('-o', '--out', help='The location to deposit this files. Defauls to this directory')

    # Finally we tell the parser to parse the arguments from the command line
    args = parser.parse_args()

    # we use this arguments to provide input to our rename function
    rename(args.inString, args.outString, duplicate = args.duplicate, outDir=args.out, regex=args.regex)

def rename(inString, outString, duplicate = True, inDir = None, outDir=None, regex=False):
    """
    A simple function to rename all the given files in a given directory
    Args:
        inString:  the input string to find and replace
        outString: the output string to replace it with
        duplicate: Whether we should duplicate the renamed files to prevent writing over the originals
        inDir: what the directory we should operate in
        outDir: the directory we should write to.
        regex: Whether we should use regex instead of simple string replace
    """
    # if not directory is provided, we use current directory
    if not inDir:
        inDir = os.getcwd()

    # if not outPut is provided, we use current directory
    if not outDir:
        outDir = inDir

    # error if outPut doesn't exist

    if not os.path.exists(outDir):
        raise IOError('%s does not exist' %outDir)
    if not os.path.exists(inDir):
        raise IOError('%s does not exist' %inDir)

    # loop over all files in current directory
    for f in os.listdir(inDir):
        # files that start with a dot are important files for the os
        logger.debug('%s is type %s' % (f, type(f)))
        if f.startswith('.'):
            continue
        # regex
        if regex:
            name = re.sub(inString, outString, f)

        else:
            name = f.replace(inString, outString)

        #same name
        if name == f:
            continue
        #construct full path
        src = os.path.join(inDir, f)
        dest = os.path.join(outDir, name)

        if duplicate:
            shutil.copy2(src, dest)
        else:
            os.rename(src, dest)


if __name__=='__main__':
    main()