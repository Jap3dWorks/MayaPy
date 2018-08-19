import sys
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
import math

nodeName = 'RippleDeformer'
# REVIEW: read abour MTypeID
nodeId = OpenMaya.MTypeId(0x102fff)

class Ripple(OpenMayaMPx.MPxDeformerNode):

    """
    Commands ----> MPxCommand
    Custom   ----> MPxNode
    Deformer ----> MPxDeformerNode
    """
    mObj_Amplitude = OpenMaya.MObject()
    mObj_Displace = OpenMaya.MObject()

    def __init__(self):
        OpenMayaMPx.MPxDeformerNode.__init__(self)
        # or super(Ripple, self).__init__()

    def deform(self, dataBlock, geoIterator, matrix, grometryIndex):
        input = OpenMayaMPx.cvar.MPxDeformerNode_input
        # 1. attach a handle to input Array Attribute
        dataHandleInputArray = dataBlock.outputArrayValue(input)
        # 2. Jump to particular element
        dataHandleInputArray.jumpToElement(grometryIndex)
        #3. attach a handle to specific data Block
        dataHandleInputElement = dataHandleInputArray.outputValue()
        #4. reach the child - inputGeom
        inputGeom = OpenMayaMPx.cvar.MPxDeformerNode_inputGeom
        dataHandleInputGeom = dataHandleInputElement.child(inputGeom)
        inMesh = dataHandleInputGeom.asMesh()

        # Envelope
        envelope = OpenMayaMPx.cvar.MPxDeformerNode_envelope
        dataHandleEnvelope = dataBlock.inputValue(envelope)
        envelopeValue = dataHandleEnvelope.asFloat()

        #Amplitude

