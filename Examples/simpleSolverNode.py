# https://download.autodesk.com/us/maya/2011help/API/simple_solver_node_8py-example.html

import maya.OpenMaya as OpenMaya
import maya.OpenMayaUI as OpenMayaUI
import maya.OpenMayaMPx as OpenMayaMPx
import maya.OpenMayaAnim as OpenMayaAnim
import math, sys

# consts
kSolverNodeName = 'spSimpleSolverNode'
kSolverNodeId = OpenMaya.MTypeId(0x8700a)


class simpleSolverNode(OpenMayaMPx.MPxIkSolverNode):
    def __init__(self):
        super(simpleSolverNode, self).__init__()

    def solverTypeName(self):
        return kSolverNodeName

    def doSolve(self):
        self.doSimpleSolver()

    def doSimpleSolver(self):
        '''
        Solve single joint in the x-y plane
        - first it calculates the angle between the handle and the end-effector.
        - then it determines which way to rotate the joint.
        '''

        handle_group = self.handleGroup()  # return a MIkHandleGroup
        handle = handle_group.handle(0)  # return a MObject
        handlePath = OpenMaya.MDagPath.getAPathTo(handle)  # Determines the Path to the specified DAG Node
        fnHandle = OpenMayaAnim.MFnIkHandle(handlePath)  # argument an Mobject, i supose we use an mdagpath,
                                                         # for possible duplicated objects

        # get the position of the end_effector
        end_effector = OpenMaya.MDagPath()
        fnHandle.getEffector(end_effector)
        tran = OpenMaya.MFnTransform(end_effector)
        effector_position = tran.rotatePivot(OpenMaya.MSpace.kWorld)

        # get the position of the handle
        handle_positions = fnHandle.rotatePivot(OpenMaya.MSpace.kWorld)

        # get the start joint position
        start_joint = OpenMaya.MDagPath()
        fnHandle.getStartJoint(start_joint)  # start_joint is filled here with the getStartJoint method
        start_tramsform = OpenMaya.MFnTransform(start_joint)
        start_position = start_tramsform.rotatePivot(OpenMaya.MSpace.kWorld)

        # calculate the rotation angle
        v1 = start_position - effector_position
        v2 = start_position - handle_positions
        angle = v1.angle(v2)

        # -------- Figure out which way to rotate --------
        #
        #  define two vectors U and V as follows
        #  U   =   EndEffector(E) - StartJoint(S)
        #  N   =   Normal to U passing through EndEffector
        #
        #  Clip handle_position to half-plane U to determine the region it
        #  lies in. Use the region to determine  the rotation direction.
        #
        #             U
        #             ^              Region      Rotation
        #             |  B
        #            (E)---N            A          C-C-W
        #         A   |                 B           C-W
        #             |  B
        #             |
        #            (S)
        #
        rot = 0.0  # Rotation about z-axis

        # U and N define a half-plane to clip the handle against
        u = effector_position - start_position
        u.normalize()

        # Get a normal to U
        zAxis = OpenMaya.MVector(0.0, 0.0, 1.0)
        N = u ^ zAxis  # cross product
        N.normalize()

        # P is the handle position vector
        P = handle_positions - effector_position

        # Determine the rotation direction
        PdotN = P[0]*N[0] + P[1]*N[1]
        if PdotN < 0:
            rot = angle  # counter-clockwise
        else:
            rot = -1.0 * angle  # clockwise

        # get and set the Joint Angles
        jointAngles = OpenMaya.MDoubleArray()
        try:
            self._getJointAngles(jointAngles)  # here fill jointAngles
        except:
            # getting angles failed, do nothing
            pass
        else:
            jointAngles.set(jointAngles[0] + rot, 0)  # set rotation in the array
            self._setJointAngles(jointAngles)  # set joint rotation

####################################################################

def nodeCreator():
    return OpenMayaMPx.asMPxPtr(simpleSolverNode())

def nodeInitializer():
    # nothing to initialize
    pass

# initialize the script plug-in
def initializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject, "Autodesk", "1.0", "Any")

    try:
        mplugin.registerNode(kSolverNodeName, kSolverNodeId, nodeCreator, nodeInitializer,
                             OpenMayaMPx.MPxNode.kIkSolverNode)
    except:
        sys.stderr.write("Failed to register node: %s" % kSolverNodeName)
        raise

# uninitialize the script plug-in
def uninitializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.deregisterNode(kSolverNodeId)
    except:
        sys.stderr.write("Failed to unregister node: %s" % kSolverNodeName)
        raise

"""
from Nodes import simpleSolverNode
reload(simpleSolverNode)
from maya import cmds
try:
    # Force is important 
    cmds.unloadPlugin('spSimpleSolverNode', force=True)
finally:
    cmds.loadPlugin(simpleSolverNode.__file__)

cmds.createNode("spSimpleSolverNode", name="spSimpleSolverNode1")
cmds.ikHandle(sol="spSimpleSolverNode1", sj="joint1", ee="joint2")
"""