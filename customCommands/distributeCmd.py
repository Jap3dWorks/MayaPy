from __future__ import division
from maya.api import OpenMaya as om
# maya know we are using new API
def maya_useNewAPI():
    pass

class distributeCmd(om.MPxCommand):
    kPluginCmdName = 'distribute'

    @classmethod
    def cmdCreator(cls):
        return cls()

    @staticmethod
    def syntaxCreator():
        syntax = om.MSyntax()

        return syntax

    def __init__(self, *args, **kwargs):
        super(distributeCmd, self).__init__(*args, **kwargs)
        self.__undoStack = []

    def doIt(self, args):
            self.redoIt()

    def redoIt(self):
        # ..
        undo = {}

        selection = om.MGlobal.getActiveSelectionList()

        if selection.length() < 3:
            om.MGlobal.displayWarning('at least 3 objects must be seleted')
            self.__undoStack.append(undo)
            return

        translations = {}
        it = om.MItSelectionList(selection, om.MFn.kTransform)

        while not it.isDone():
            node = it.getDagPath()
            tranFn = om.MFnTransform(node)

            name = node.partialPathName()
            # We then get the transform values and add them to two separate dictionaries
            # One to modify and one to store for later undoing
            # Remember that dictionaries are mutable which means even if we have two references
            # to a dictionary, they share the same data
            translations[name] = tranFn.translation(om.MSpace.kWorld)
            undo[name] = tranFn.translation(om.MSpace.kWorld)

            it.next()

        self.__undoStack.append(undo)

        for i, axis in enumerate('xyz'):
            # We'll use the enumerate counter to filter our MVectors to just the axis we care about
            axes = [t[i] for t in translations.values()]

            # get min and max
            minVal = min(axes)
            maxVal = max(axes)

            # sort the the node list by their position in the given axis
            # don't undertand well the value of x// sortd ascendent order
            # i think X = key -> [Transform][axis] -> axis value of that transformation -> ascendent order
            nodes = sorted(translations.keys(), key=lambda x: translations[x][i])

            # steps for the distribution
            steps = (maxVal-minVal)/(len(nodes)-1)

            for x, node in enumerate(nodes):
                translations[node][i] = (minVal + (x*steps))

        it.reset()
        while not it.isDone():
            node = it.getDagPath()
            tranFn = om.MFnTransform(node)

            #look position in our dictionary using its partial name
            translation = translations[node.partialPathName()]

            #set transform in world space position
            tranFn.setTranslation(translation, om.MSpace.kWorld)

            # remember go to the next item
            it.next()

    def isUndoable(self):
        return True

    def undoIt(self):
        if not self.__undoStack:
            return

        # then we pop the last item, which is the mos recent, off the end of our undoStack
        # .pop() if not given value return and remove the las item
        translations = self.__undoStack.pop()

        # if this was empty, then do anything
        if not translations:
            return

        # finally reconstruct our selection and set transforms back
        # we make an empty selection list
        sList = om.MSelectionList()

        for i, node in enumerate(translations):
            # add item to our selection list
            sList.add(node)
            # get it's dag path
            node = sList.getDagPath(i)
            # construct a MFnTransform (object for move)
            tranFn = om.MFnTransform(node)

            #set transforms back to our cached value
            tranFn.setTranslation(translations[node.partialPathName()], om.MSpace.kWorld)

def initializePlugin(plugin):
    pluginFn = om.MFnPlugin(plugin)
    try:
        pluginFn.registerCommand(
            distributeCmd.kPluginCmdName,
            distributeCmd.cmdCreator,
            distributeCmd.syntaxCreator
        )
    except:
        om.MGlobal.displayError('Failed to register  command: %s' % distributeCmd.kPluginCmdName)
        raise

def uninitializePlugin(plugin):
    pluginFn = om.MFnPlugin(plugin)
    try:
        pluginFn.deregisterCommand(DistributeCmd.kPluginCmdName)
    except:
        om.MGlobal.displayError('Failed to deregister command: %s' % distributeCmd.kPluginCmdName)
        raise

"""
To call this
from Commands import distributeCmd
import maya.cmds as mc
try:
    # Force is important because of the undo stack
    mc.unloadPlugin('distributeCmd', force=True)
finally:
    mc.loadPlugin(distributeCmd.__file__)
mc.distribute()
"""