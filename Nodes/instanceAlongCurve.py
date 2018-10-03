# documentation: https://github.com/mmerchante/instanceAlongCurve/blob/master/instanceAlongCurve.py
# for study purposes:
# original script via mmerchante
# https://github.com/mmerchante

import sys
import math
import random
import traceback
import maya.mel as mel
import pymel.core as pm
import maya.OpenMaya as OpenMaya
import maya.OpenMayaUI as OpenMayaUI
import maya.OpenMayaMPx as OpenMayaMPx
import maya.OpenMayaRender as OpenMayaRender

kPluginVersion = "0.0"
kPluginCmdName = "instanceAlongCurve"
kPluginCtxCmdName = "instanceAlongCurveCtx"
kPluginNodeName = 'instanceAlongCurveLocator'
kPluginManipNodeName = 'instanceAlongCurveLocatorManip'
kPluginNodeClassify = 'utility/general'
kPluginNodeId = OpenMaya.MTypeId(0x05555)
kPluginNodeManipId = OpenMaya.MTypeId(0x05556)

class instanceAlongCurveLocator(OpenMayaMPx.MPxLocatorNode):

    # simple container class for compound vector attributes
    class Vector3CompoundAttribute(object):
        def __init__(self):
            self.compound = OpenMaya.MObject()
            self.x = OpenMaya.MObject()
            self.y = OpenMaya.MObject()
            self.z = OpenMaya.MObject()

    class CurveAxisHandleAttribute(object):
        def __init__(self):
            self.compound = OpenMaya.MObject()
            self.parameter = OpenMaya.MObject()
            self.angle = OpenMaya.MObject()  # angle over tangent axis

    # Attributes:
    # Legacy attributes to support backward compatibility
    legacyInputTransformAttr = OpenMaya.MObject()

    # input attributes
    inputCurveAttr = OpenMaya.MObject()
    inputTransformAttr = OpenMaya.MObject()
    inputShadingGroupAttr = OpenMaya.MObject()

    # translation offsets
    inputLocalTranslationOffsetAttr = OpenMaya.MObject()
    inputGlobalTranslationOffsetAttr = OpenMaya.MObject()

    # rotation offset
    inputLocalRotationOffsetAttr = OpenMaya.MObject()
    inputGlobalRotationOffsetAttr = OpenMaya.MObject()

    # Scale offset
    inputLocalScaleOffsetAttr = OpenMaya.MObject()

    # Instance count related attributes
    instanceCountAttr = OpenMaya.MObject()
    instancingModeAttr = OpenMaya.MObject()
    instanceLengthAttr = OpenMaya.MObject()
    maxInstancesByLengthAttr = OpenMaya.MObject()

    # Curve axis data, to be manipulated by user
    enableManipulatorsAttr = OpenMaya.MObject()
    curveAxisHandleAttr = CurveAxisHandleAttribute()
    curveAxisHandleCountAttr = OpenMaya.MObject()

    displayTypeAttr = OpenMaya.MObject()
    bboxAttr = OpenMaya.MObject()

    orientationModeAttr = OpenMaya.MObject()
    inputLocalOrientationAxisAttr = OpenMaya.MObject()

    # what is this class for?
    class RampAttributes(object):
        def __init__(self):
            self.ramp = OpenMaya.MObject()  # normalized ramp
            self.rampOffset = OpenMaya.MObject()  # evaluation offset for ramp
            self.rampAxis = OpenMaya.MObject()  # ramp normalized axis
            self.rampAmplitude = OpenMaya.MObject()  # ramp amplitude
            self.rampRandomAmplitude = OpenMaya.MObject()  # ramp random amplotude
            self.rampRepeat = OpenMaya.MObject()

    # simple container class for compound vector attributes
    class rampValueContainer(object):
        def __init__(self, mObject, dataBlock, rampAttr, normalize, instanceCount):
            self.ramp = OpenMaya.MRampAttribute(OpenMaya.MPlug(mObject, rampAttr.ramp))
            self.rampOffset = dataBlock.inputValue(rampAttr.rampOffset).asFloat()
            self.rampRandomAmplitude = dataBlock.inputValue(rampAttr.randomAmplitude).asFloat()
            self.rampAmplitude = dataBlock.inputValue(rampAttr.rampAmplitude).asFloat()
            self.rampRepeat = dataBlock.inputValue(rampAttr.rampRepeat).asFloat()

            if normalize:
                self.rampAxis = dataBlock.inputValue(rampAttr.rampAxis.compound).asVector().normal()
            else:
                self.rampAxis = dataBlock.inputValue(rampAttr.rampAxis.compound).asVector()

            self.useDynamicAmplitudeValues = False

            amplitudePlug = OpenMaya.MPlug(mObject, rampAttr.rampAmplitude)