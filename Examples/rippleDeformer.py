import sys
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
import math

# EXPLANATION cvar.MPXDeformerNode_Input or ouput
# By inheriting from MPxDeformerNode, your class will have access to the input and output mesh attributes,
# available via OpenMayaMPx.cvar.MPxGeometryFilter_inputGeom and
# OpenMayaMPx.cvar.MPxGeometryFilter_outputGeom respectively.
# https://knowledge.autodesk.com/search-result/caas/CloudHelp/cloudhelp/2016/ENU/Maya-SDK/files/GUID-10CE99A6-2C32-49E1-85ED-2E2F6782CF23-htm.html
# REVIEW: OpenMayaMPx.cvar.MPxDeformerNode_input for earlier versions of maya 2016

inputAttr = OpenMayaMPx.cvar.MPxGeometryFilter_input
outputGeom = OpenMayaMPx.cvar.MPxGeometryFilter_outputGeom
inputGeom = OpenMayaMPx.cvar.MPxGeometryFilter_inputGeom
envelope = OpenMayaMPx.cvar.MPxGeometryFilter_envelope

class Ripple(OpenMayaMPx.MPxDeformerNode):
    """
    Commands ----> MPxCommand
    Custom   ----> MPxNode
    Deformer ----> MPxDeformerNode
    """
    # node info
    nodeName = 'RippleDeformer'
    # REVIEW: read abour MTypeID
    nodeId = OpenMaya.MTypeId(0x102fff)

    # attributes
    mObj_Amplitude = OpenMaya.MObject()
    mObj_Displace = OpenMaya.MObject()

    @classmethod
    def creator(cls):
        # how to run the class, in maya API 2 this is not necessary
        return OpenMayaMPx.asMPxPtr(cls())

    @staticmethod
    def initialize():
        # adding attributes
        mFnAttr = OpenMaya.MFnNumericAttribute()
        Ripple.mObj_Amplitude = mFnAttr.create('AmplitudeValue', 'AmplitudeVal', OpenMaya.MFnNumericData.kFloat, 0.0)
        mFnAttr.setKeyable(True)
        mFnAttr.setMin(0.0)
        mFnAttr.setMax(1.0)

        Ripple.mObj_Displace = mFnAttr.create('DisplaceValue', 'DisplaceVal', OpenMaya.MFnNumericData.kFloat, 0.0)
        mFnAttr.setKeyable(True)
        mFnAttr.setMin(0.0)
        mFnAttr.setMax(100.0)

        Ripple.addAttribute(Ripple.mObj_Displace)
        Ripple.addAttribute(Ripple.mObj_Amplitude)

        """
        SWIG = Simplified Wrapper Interface Generator
        """
        Ripple.attributeAffects(Ripple.mObj_Amplitude, outputGeom)
        Ripple.attributeAffects(Ripple.mObj_Displace, outputGeom)

    def __init__(self):
        OpenMayaMPx.MPxDeformerNode.__init__(self)
        # or super(Ripple, self).__init__()

    # EXPLANATION: MPxGeometryFilter.deform()
    # this method performs the deformation algorithm. geometry iterator passed is in Local Space.
    # To convert points to world space use the matrix that is suppied.
    def deform(self, dataBlock, geoIterator, matrix, grometryIndex):
        """
        Args:
            dataBlock: the node's datablock. MDataBlock
            geoIterator: an iterator for the current geometry being deformed. MItGeometry
            matrix: the geometry's world space transformation matrix. MMatrix
            grometryIndex: the index corresponding to the requested output geometry. Unsigned Int
        """
        # print 'hi i am inputAttr %s:' % inputAttr
        # print 'hi i am inputGeom %s:' % inputGeom
        # print 'hi i am outputGeom %s:' % outputGeom

        # 1. attach a handle to input Array Attribute
        # EXPLANATION: MDataBlock: provides storage for the data being received by or sent by the node.
        dataHandleInputArray = dataBlock.outputArrayValue(inputAttr)
        # 2. Jump to particular element and get the desired output by geometryIndex
        dataHandleInputArray.jumpToElement(grometryIndex)
        # 3. attach a handle to specific data Block
        dataHandleInputElement = dataHandleInputArray.outputValue()
        # 4. reach the child - inputGeom
        dataHandleInputGeom = dataHandleInputElement.child(inputGeom)
        inMesh = dataHandleInputGeom.asMesh()

        # Envelope
        dataHandleEnvelope = dataBlock.inputValue(envelope)
        # get envelope Value inserted by the user
        envelopeValue = dataHandleEnvelope.asFloat()

        # Amplitude, editable value
        dataHandleAmplitude = dataBlock.inputValue(self.mObj_Amplitude)
        amplitudeValue = dataHandleAmplitude.asFloat()

        # Displace, editable value
        dataHandleDisplace = dataBlock.inputValue(self.mObj_Displace)
        displaceValue = dataHandleDisplace.asFloat()

        mFloatVectorArray_normal = OpenMaya.MFloatVectorArray()
        mFnMesh = OpenMaya.MFnMesh(inMesh)
        mFnMesh.getVertexNormals(False, mFloatVectorArray_normal, OpenMaya.MSpace.kObject)

        mPointArray_meshVert = OpenMaya.MPointArray()
        while not geoIterator.isDone():
            pointPosition = geoIterator.position()
            pointPosition.x = pointPosition.x + math.sin(geoIterator.index() + displaceValue) * amplitudeValue * mFloatVectorArray_normal[geoIterator.index()].x * envelopeValue
            pointPosition.y = pointPosition.y + math.sin(geoIterator.index() + displaceValue) * amplitudeValue * mFloatVectorArray_normal[geoIterator.index()].y * envelopeValue
            pointPosition.z = pointPosition.z + math.sin(geoIterator.index() + displaceValue) * amplitudeValue * mFloatVectorArray_normal[geoIterator.index()].z * envelopeValue
            mPointArray_meshVert.append(pointPosition)

            geoIterator.next()

        geoIterator.setAllPositions(mPointArray_meshVert)

def initializePlugin(mObject):
    mplugin = OpenMayaMPx.MFnPlugin(mObject)
    try:
        mplugin.registerNode(Ripple.nodeName, Ripple.nodeId, Ripple.creator, Ripple.initialize, OpenMayaMPx.MPxNode.kDeformerNode)
    except:
        sys.stderr.write('Failed to register node: %s' % Ripple.nodeName)
        raise

def uninitializePlugin(mObject):
    mplugin = OpenMayaMPx.MFnPlugin(mObject)
    try:
        mplugin.deregisterNode(Ripple.nodeId)
    except:
        sys.stderr.write('Failed to deregister node: %s' % Ripple.nodeName)
        raise


"""
    to load:
    from Nodes import rippleDeformer
    import maya.cmds as mc
    try:
        # Force is important 
        mc.unloadPlugin('RippleDeformer', force=True)
    finally:
        mc.loadPlugin(rippleDeformer.__file__)
    
    mc.polySphere()
    mc.deformer(type='RippleDeformer')
"""
