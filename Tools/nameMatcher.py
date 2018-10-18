# introduce part name don't pair. create list of lists with pairs
from maya import cmds

import pymel.core as pm
import re

import logging
logging.basicConfig()
logger = logging.getLogger('Fbx Exporter UI:')
logger.setLevel(logging.INFO)


class nameMatcher(list):
    def __init__(self):
        super(nameMatcher, self).__init__()
        self.initialSet = []

    def MatchFromSelection(self, *args):
        # no pymel, because pymel return class nodes, we need simple strings
        self.initialSet = set(cmds.ls(sl=True))
        assert len(self.initialSet) > 2, 'Select at least two elments'

        while len(self.initialSet):
            firstElement = self.initialSet.pop()
            # store match elements in matchElements
            matchElements = []

            # iterate for key word
            for arg in args:
                # check if key word is in first pop element

                if arg in firstElement:
                    matchElements.append(firstElement)
                    # prepare new set without first arg
                    restArgs = set(args)
                    restArgs.remove(arg)

                    # iterate again with rest of key words to find match elements
                    for restArg in restArgs:
                        searchElements = firstElement.replace(arg, restArg)
                        try:
                            # if remove do not find element, give us an error
                            self.initialSet.remove(searchElements)
                            matchElements.append(searchElements)
                        except:
                            logger.debug('%s not found' % searchElements)
                            pass

                    # avoid unnecessary iterations
                    break

                logger.debug('%s not found in %s' % (arg, firstElement))

            self.append(matchElements)