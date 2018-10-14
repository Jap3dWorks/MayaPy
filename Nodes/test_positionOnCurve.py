from cmt.test import TestCase
from Nodes import positionOnCurve
reload(positionOnCurve)
from maya import cmds

class SampleTests(TestCase):
    def runTest(self):
        pass

    def connect_Cube_PositionCurve(self):
        cmds.flushUndo()
        cmds.file(force=True, new=True)
        
        cmds.unloadPlugin('positionOnCurve', force=True)
        
        # Force is important because of the undo stack
        cmds.loadPlugin(positionOnCurve.__file__)
        
        
        #list curves
        curveNode = cmds.curve(p=[(0,0,0), (5,0,0), (10,0,0), (20,10,5), (20,15,10), (20,20,15)], k=[0, 0, 0, 3, 7, 10, 10, 10])
        #list shape
        transformNode = cmds.polyCube()[0]
        

        
        positionOnCurveNode=cmds.createNode('positionOnCurve', name='positionOnCurve')
        decomposeMatrixNode=cmds.createNode('decomposeMatrix', name='decomposeMatrix')
        cmds.connectAttr('%s.Transformation' % positionOnCurveNode, '%s.inputMatrix' % decomposeMatrixNode)
        
        cmds.connectAttr('%s.worldSpace' % curveNode, '%s.Curve' % positionOnCurveNode)
        cmds.connectAttr('%s.outputTranslate' % decomposeMatrixNode, '%s.translate' % transformNode)
        cmds.connectAttr('%s.outputRotate' % decomposeMatrixNode, '%s.rotate' % transformNode)
        
    def initialize_Node_and_command(self):
        cmds.flushUndo()
        cmds.file(force=True, new=True)

        cmds.unloadPlugin('positionOnCurve.py', force=True)
        # Force is important because of the undo stack
        cmds.loadPlugin(positionOnCurve.__file__)

        # list curves
        curveNode = cmds.curve(p=[(0, 0, 0), (5, 0, 0), (10, 0, 0), (20, 10, 5), (20, 15, 10), (20, 20, 15)],
                               k=[0, 0, 0, 3, 7, 10, 10, 10])
        # list shape
        transformNode = cmds.polyCube()[0]

        cmds.select(clear=True)
        cmds.select(curveNode)
        cmds.select(transformNode, add=True)

        cmds.positionOnCurveCommand()
        
        
"""
from Nodes import test_positionOnCurve
reload(test_positionOnCurve)
from maya import cmds

sampleTest = test_positionOnCurve.SampleTests()
sampleTest.connect_Cube_PositionCurve()
"""