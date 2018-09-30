# pyAnimCubeNode.py

import sys
import maya.api.OpenMaya as OpenMaya


def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, objects created using the Maya Python API 2.0.
    """
    pass


kPluginNodeName = "spAnimCube"
kPluginNodeId = OpenMaya.MTypeId(0x8700B)


##########################################################
# Plug-in
##########################################################
class animCube(OpenMaya.MPxNode):
    time = OpenMaya.MObject()
    outputMesh = OpenMaya.MObject()

    def __init__(self):
        ''' Constructor. '''
        OpenMaya.MPxNode.__init__(self)

    def createMesh(self, tempTime, outData):
        '''
        Create a cube mesh, and scale it given the current frame number.
        The resulting mesh data is stored within outData.
        '''

        frame = int(tempTime.asUnits(OpenMaya.MTime.kFilm))
        if frame is 0:
            frame = 1

        cubeSize = 0.5 * float(frame % 10)

        numPolygons = 6
        numVertices = 8
        numPolygonConnects = 4 * numPolygons  # four vertices are needed per polygon. (i.e. 24 numPolygonConnects)

        vertexArray = OpenMaya.MFloatPointArray()
        vertexArray.setLength(numVertices)
        vertexArray[0] = OpenMaya.MFloatPoint(-cubeSize, -cubeSize, -cubeSize)
        vertexArray[1] = OpenMaya.MFloatPoint(cubeSize, -cubeSize, -cubeSize)
        vertexArray[2] = OpenMaya.MFloatPoint(cubeSize, -cubeSize, cubeSize)
        vertexArray[3] = OpenMaya.MFloatPoint(-cubeSize, -cubeSize, cubeSize)
        vertexArray[4] = OpenMaya.MFloatPoint(-cubeSize, cubeSize, -cubeSize)
        vertexArray[5] = OpenMaya.MFloatPoint(-cubeSize, cubeSize, cubeSize)
        vertexArray[6] = OpenMaya.MFloatPoint(cubeSize, cubeSize, cubeSize)
        vertexArray[7] = OpenMaya.MFloatPoint(cubeSize, cubeSize, -cubeSize)

        polygonCounts = OpenMaya.MIntArray()
        polygonCounts.setLength(numPolygons)
        for i in range(0, numPolygons):
            polygonCounts[i] = 4

        polygonConnects = OpenMaya.MIntArray()
        polygonConnects.setLength(numPolygonConnects)
        polygonConnects[0] = 0
        polygonConnects[1] = 1
        polygonConnects[2] = 2
        polygonConnects[3] = 3
        polygonConnects[4] = 4
        polygonConnects[5] = 5
        polygonConnects[6] = 6
        polygonConnects[7] = 7
        polygonConnects[8] = 3
        polygonConnects[9] = 2
        polygonConnects[10] = 6
        polygonConnects[11] = 5
        polygonConnects[12] = 0
        polygonConnects[13] = 3
        polygonConnects[14] = 5
        polygonConnects[15] = 4
        polygonConnects[16] = 0
        polygonConnects[17] = 4
        polygonConnects[18] = 7
        polygonConnects[19] = 1
        polygonConnects[20] = 1
        polygonConnects[21] = 7
        polygonConnects[22] = 6
        polygonConnects[23] = 2

        meshFn = OpenMaya.MFnMesh()
        newMesh = meshFn.create(vertexArray, polygonCounts, polygonConnects, parent=outData)

    def compute(self, plug, data):
        if plug == animCube.outputMesh:
            timeData = data.inputValue(animCube.time)
            tempTime = timeData.asTime()

            outputHandle = data.outputValue(animCube.outputMesh)

            dataCreator = OpenMaya.MFnMeshData()
            newOutputData = dataCreator.create()

            self.createMesh(tempTime, newOutputData)

            outputHandle.setMObject(newOutputData)
            data.setClean(plug)
        else:
            return OpenMaya.kUnknownParameter


##########################################################
# Plug-in initialization.
##########################################################
def nodeCreator():
    ''' Creates an instance of our node class and delivers it to Maya as a pointer. '''
    return animCube()


def nodeInitializer():
    ''' Defines the input and output attributes as static variables in our plug-in class. '''
    unitAttr = OpenMaya.MFnUnitAttribute()
    typedAttr = OpenMaya.MFnTypedAttribute()

    animCube.time = unitAttr.create("time", "tm", OpenMaya.MFnUnitAttribute.kTime, 0.0)
    animCube.outputMesh = typedAttr.create("outputMesh", "out", OpenMaya.MFnData.kMesh)

    animCube.addAttribute(animCube.time)
    animCube.addAttribute(animCube.outputMesh)

    animCube.attributeAffects(animCube.time, animCube.outputMesh)


def initializePlugin(mobject):
    ''' Initialize the plug-in '''
    mplugin = OpenMaya.MFnPlugin(mobject)
    try:
        mplugin.registerNode(kPluginNodeName, kPluginNodeId, nodeCreator, nodeInitializer)
    except:
        sys.stderr.write("Failed to register node: " + kPluginNodeName)
        raise


def uninitializePlugin(mobject):
    ''' Uninitializes the plug-in '''
    mplugin = OpenMaya.MFnPlugin(mobject)
    try:
        mplugin.deregisterNode(kPluginNodeId)
    except:
        sys.stderr.write("Failed to deregister node: " + kPluginNodeName)
        raise


##########################################################
# Sample usage.
##########################################################
''' 
# Copy the following lines and run them in Maya's Python Script Editor:

import maya.cmds as cmds
cmds.loadPlugin(pyAnimCubeNode.__file)
cmds.createNode( "transform", name="animCube1" )
cmds.createNode( "mesh", name="animCubeShape1", parent="animCube1" )
cmds.sets( "animCubeShape1", add="initialShadingGroup" )
cmds.createNode( "spAnimCube", name="animCubeNode1" )
cmds.connectAttr( "time1.outTime", "animCubeNode1.time" )
cmds.connectAttr( "animCubeNode1.outputMesh", "animCubeShape1.inMesh" )

'''