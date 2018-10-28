from cmt.test import TestCase
from TESTFOLDER import elevatorNode

reload(elevatorNode)
from maya import cmds

class SampleTests(TestCase):
    def runTest(self):
        pass

    def elevatorNode_Create(self):
        cmds.flushUndo()
        cmds.file(force=True, new=True)
        
        cmds.unloadPlugin('elevatorNode', force=True)
        
        # Force is important because of the undo stack
        cmds.loadPlugin(elevatorNode.__file__)

        #list shape
        transformNode01 = cmds.polyCube(w=8.465834, h=0.584901, d=8.465834)[0]
        transformNode02 = cmds.polyCube(w=8.465834, h=0.584901, d=8.465834)[0]
        stick = cmds.polyCube(w=8.465834, h=0.584901, d=0.507098)[0]
        cmds.xform(transformNode01, rp=(-3.891191,0,0), sp=(-3.891191,0,0))
        cmds.xform(transformNode02, rp=(-3.891191, 0, 0), sp=(-3.891191, 0, 0))
        cmds.xform(stick, rp=(-3.891191, 0, 0), sp=(-3.891191, 0, 0))
        cmds.xform(transformNode02, ws=True, t=(0.0, 15, 0.0))
        pluginNode = cmds.createNode('elevatorLocator')

        #decomposeMatrixNode=cmds.createNode('decomposeMatrix', name='decomposeMatrix')
        cmds.connectAttr('%s.worldMatrix' % transformNode01, '%s.Matrix01' % pluginNode)
        cmds.connectAttr('%s.worldMatrix' % transformNode02, '%s.Matrix02' % pluginNode)
        cmds.connectAttr('%s.message' % stick, '%s.Object' % pluginNode)
        
        
"""
from Nodes import test_positionOnCurve
reload(test_positionOnCurve)
from maya import cmds

sampleTest = test_positionOnCurve.SampleTests()
sampleTest.connect_Cube_PositionCurve()
"""