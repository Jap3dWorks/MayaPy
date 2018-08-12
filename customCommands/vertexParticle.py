import sys
# using old api
from maya import OpenMaya as OpenMaya
from maya import OpenMayaMPx as OpenMayaMPx
from maya import OpenMayaFX as OpenMayaFX

commandName = 'vertexParticle'

kHelpFlag = '-h'
kHelpLongFlag = '-help'
kSparseFlag = '-s'
kSparseLongFlag = '-sparse'
helpMessage = 'This command is used to attach a particle on each vertex of a polyMesh'

class pluginCommand(OpenMayaMPx.MPxCommand):
    sparse = None
    def __init__(self):
        super(pluginCommand, self).__init__()

    # here the command show what arguments are introduced?
    def argumentParser(self, argList):
        syntax = self.syntax()
        try:
            parsedArguments = OpenMaya.MArgDatabase(syntax, argList)
        except:
            print 'Incorrect Argument'
            return OpenMaya.kUnknownParameter

        if parsedArguments.isFlagSet(kSparseFlag):
            self.sparse = parsedArguments.flagArgumentDouble(kSparseFlag, 0)
        if parsedArguments.isFlagSet(kSparseLongFlag):
            self.sparse = parsedArguments.flagArgumentDouble(kSparseLongFlag, 0)
        if parsedArguments.isFlagSet(kHelpFlag):
            self.setResult(helpMessage)
        if parsedArguments.isFlagSet(kHelpLongFlag):
            self.setResult(helpMessage)

    # the command can do ctr+z
    def isUndoable(self):
        return True

    def undoIt(self):
        print 'undo'
        # we have the particle but not the transform node in mFnDagNode
        mFnDagNode = OpenMaya.MFnDagNode(self.mObj_particle)
        # so we create an object to delete the particle system
        mDagMod = OpenMaya.MDagModifier()
        # and use the .parent fn to find the transform node
        mDagMod.deleteNode(mFnDagNode.parent(0))
        mDagMod.doIt()

    def redoIt(self):
        mSel = OpenMaya.MSelectionList()
        mDagPath = OpenMaya.MDagPath()
        mFnMesh = OpenMaya.MFnMesh()
        OpenMaya.MGlobal.getActiveSelectionList(mSel) # return a MselectionList of current selection
        if mSel.length() >= 1:
            try:
                mSel.getDagPath(0, mDagPath)
                mFnMesh.setObject(mDagPath)
            except:
                print 'Select a polymesh'
                return OpenMaya.kUnknownParameter

        else:
            print 'Select a polymesh'
            return OpenMaya.kUnknownParameter

        # store vertex points in a MPointArray
        mPointArray = OpenMaya.MPointArray()
        mFnMesh.getPoints(mPointArray, OpenMaya.MSpace.kWorld)

        # Create a particle system
        mFnParticle = OpenMayaFX.MFnParticleSystem()
        self.mObj_particle = mFnParticle.create()

        # to fix maya bug
        mFnParticle = OpenMayaFX.MFnParticleSystem(self.mObj_particle)

        counter = 0
        for i in xrange(mPointArray.length()):
            # don't understand this
            if (i % self.sparse) == 0:
                mFnParticle.emit(mPointArray[i])
                counter += 1
        print 'Total points: %s' % str(counter)
        mFnParticle.saveInitialState()
        print 'This is self.sparse %s' %self.sparse

    def doIt(self, argList):
        print "doIt..."
        self.argumentParser(argList)
        if self.sparse != None:
            self.redoIt()

# creator
def cmdCreator():
    return OpenMayaMPx.asMPxPtr(pluginCommand())

def syntaxCreator():
    # create mSyntax Object
    syntax = OpenMaya.MSyntax()

    #add the flags
    syntax.addFlag(kHelpFlag, kHelpLongFlag)
    syntax.addFlag(kSparseFlag, kSparseLongFlag, OpenMaya.MSyntax.kDouble)

    # return syntax
    return syntax

def initializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.registerCommand(commandName, cmdCreator, syntaxCreator)
    except:
        sys.stderr.write('Failed to register command: %s \n' %commandName)

def uninitializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.deregisterCommand(commandName)
    except:
        sys.stderr.write('Failed to unregister command: %s \n' %commandName)