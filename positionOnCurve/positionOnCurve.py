import sys

import maya.OpenMaya as OpenMaya
import maya.OpenMayaUI as OpenMayaUI
import maya.OpenMayaMPx as OpenMayaMPx

import math
import pymel.core as pm
import maya.cmds as cmds
import maya.mel as mel

import logging
logging.basicConfig()
logger = logging.getLogger('Position on curve:')
logger.setLevel(logging.INFO)

# documentation: https://help.autodesk.com/view/MAYAUL/2018/ENU/?guid=__files_GUID_AABB9BB4_816F_4C7C_A526_69B0568E1587_htm
# documentation: https://help.autodesk.com/view/MAYAUL/2018/ENU/?guid=__files_GUID_767D6572_552D_4D94_90E2_AE626F276D37_htm
# documentation: https://help.autodesk.com/view/MAYAUL/2018/ENU/?guid=__files_GUID_C5A68952_EB7D_41CC_ABF5_CC4C63293EED_htm
# documentation: https://stackoverflow.com/questions/50365958/maya-mpxnode-multiple-outputs

# TODO: Study object creation and new plugs inside Node, this works with callbacks
# TODO: add twist

kPluginVersion = "0.0"
kPluginNodeName = 'positionOnCurve'
# identifier of the node
kPluginNodeId = OpenMaya.MTypeId(0x87059)
kPluginNodeClassify = 'utility/general'
kPluginNodeNameManip = 'positionOnCurveManip'
kPluginNodeNameManipId = OpenMaya.MTypeId(0x87060)
kPluginNodeNameCommand = 'positionOnCurveCommand'
kPluginNodeClassify = 'utility/general'  # not in use

# we use the maya locator proxy as base class for our node
class positionOnCurve(OpenMayaMPx.MPxLocatorNode):
    # define inputs
    inputCurveAttribute = OpenMaya.MObject()
    curvePositionAttribute = OpenMaya.MObject()
    rampScaleAttr = OpenMaya.MObject()
    rampTwistAttr = OpenMaya.MObject()

    # define outputs
    outputMatrixTransformAttribute = OpenMaya.MObject()

    @classmethod
    def creator(cls):
        # node creator for classic python API
        return OpenMayaMPx.asMPxPtr(cls())

    @staticmethod
    def nodeInitializer():
        # associate node with its manipulator
        OpenMayaMPx.MPxManipContainer.addToManipConnectTable(kPluginNodeId)

        # To make things more readable
        node = positionOnCurve

        # Ramp attributes
        rampAttrFn = OpenMaya.MRampAttribute()
        node.rampScaleAttr = rampAttrFn.createCurveRamp('rampScaleAttr', 'rampScaleAttr')
        node.addAttribute(node.rampScaleAttr)
        # rampTwistAttr
        rampAttrFn = OpenMaya.MRampAttribute()
        node.rampTwistAttr = rampAttrFn.createCurveRamp('rampTwistAttr', 'rampTwistAttr')
        node.addAttribute(node.rampTwistAttr)

        # create attributes
        mfnAttr = OpenMaya.MFnNumericAttribute()

        # positionAttr
        node.curvePositionAttribute = mfnAttr.create('PositionCurve', 'PositionCurve', OpenMaya.MFnNumericData.kDouble, 0.5)
        mfnAttr.setKeyable(True)
        mfnAttr.setStorable(True)
        mfnAttr.setWritable(True)
        mfnAttr.setMin(0.0)
        mfnAttr.setMax(1.0)
        # add attributes just after create attribute
        node.addAttribute(node.curvePositionAttribute)

        # transformationAttr
        mfnAttr = OpenMaya.MFnMatrixAttribute()
        node.outputMatrixTransformAttribute = mfnAttr.create('Transformation', 'Transformation', OpenMaya.MFnNumericData.kDouble)  # 1 double precision
        mfnAttr.setKeyable(False)
        mfnAttr.setStorable(True)
        mfnAttr.setReadable(True)
        mfnAttr.setWritable(False)
        mfnAttr.setHidden(False)
        node.addAttribute(node.outputMatrixTransformAttribute)

        # curveAttr
        # explanation: curve input OpenMaya.MFnData.kNurbsCurve. no OpenMaya.MFn.kNurbsCurve
        mfnAttr = OpenMaya.MFnTypedAttribute()
        node.inputCurveAttribute = mfnAttr.create('Curve', 'Curve', OpenMaya.MFnData.kNurbsCurve)
        mfnAttr.setKeyable(False)
        mfnAttr.setStorable(False)
        mfnAttr.setReadable(False)
        mfnAttr.setWritable(True)
        mfnAttr.setHidden(False)
        node.addAttribute(node.inputCurveAttribute)

        # define attributes relations to update
        node.attributeAffects(node.inputCurveAttribute, node.outputMatrixTransformAttribute)
        node.attributeAffects(node.curvePositionAttribute, node.outputMatrixTransformAttribute)

        # rampAttr
        node.attributeAffects(node.rampScaleAttr, node.outputMatrixTransformAttribute)
        node.attributeAffects(node.rampTwistAttr, node.outputMatrixTransformAttribute)

        return True

    def __init__(self):
        # return to super
        OpenMayaMPx.MPxLocatorNode.__init__(self)

    def postConstructor(self):
        OpenMaya.MFnDependencyNode(self.thisMObject()).setName('positionOnCurveShape#')
        # define a callback, here we can for example duplicate objects and connect
        # (for that porpouse we need array attr).
        self.callbackID = OpenMaya.MNodeMessage.addAttributeChangedCallback(self.thisMObject(), self.attrChangeCallback)

    def attrChangeCallback(self, *args):
        logger.debug('CallBack ## attr changed ##')

    def isBounded(self):
        return True

    def boundingBox(self):
        return OpenMaya.MBoundingBox(OpenMaya.MPoint(-1, -1, -1), OpenMaya.MPoint(1, 1, 1))

    # plug represents output attribute
    # dataBlock all values
    def compute(self, pPlug, pDataBlock):
        logger.debug('--Compute Method--')
        if pPlug != self.outputMatrixTransformAttribute:  # Review: self.
            return None

        #  data handles for each attribute and values
        inputCurveHandle = pDataBlock.inputValue(positionOnCurve.inputCurveAttribute)  # get mDataHandle
        inputCurve = inputCurveHandle.asNurbsCurveTransformed()  # mObject

        curvePositionHandle = pDataBlock.inputValue(positionOnCurve.curvePositionAttribute)  # get mDataHandle
        curvePosition = curvePositionHandle.asDouble()  # asDouble

        # rampScaleAttr, don't use dataBlock. MRampAttribute instead
        rampScaleHandle = OpenMaya.MRampAttribute(OpenMaya.MPlug(self.thisMObject(), positionOnCurve.rampScaleAttr))
        rampTwistHandle = OpenMaya.MRampAttribute(OpenMaya.MPlug(self.thisMObject(), positionOnCurve.rampTwistAttr))

        # convert data to C++ types
        # rampScaleValue
        util = OpenMaya.MScriptUtil()
        util.createFromDouble(0.0)
        valuePtr = util.asFloatPtr()
        rampScaleHandle.getValueAtPosition(curvePosition, valuePtr)

        # read value from memory
        rampScaleValue = util.getFloat(valuePtr)

        #TwistScaleValue
        util = OpenMaya.MScriptUtil()
        util.createFromDouble(0.0)
        valuePtr = util.asFloatPtr()
        rampTwistHandle.getValueAtPosition(curvePosition, valuePtr)

        # read value from memory
        rampTwistValue = util.getFloat(valuePtr)

        # outputHandle
        outputMatrixTransformHandle = pDataBlock.outputValue(positionOnCurve.outputMatrixTransformAttribute)  # get mDataHandle

        # compute
        # create curves fn
        inputCurveMfn = OpenMaya.MFnNurbsCurve(inputCurve)
        curveLenght = inputCurveMfn.length()
        pointPosition = curvePosition * curveLenght
        curveParam = inputCurveMfn.findParamFromLength(pointPosition)

        # get Vectors
        curveNormal = inputCurveMfn.normal(max(curveParam - 0.001, 0.001))
        curveTangent = inputCurveMfn.tangent(curveParam)
        curveBinormal = curveTangent ^ curveNormal

        # rampTwist
        rampTwistValue = (rampTwistValue - 0.5) * math.pi * 2  # possible add magnitude
        util = OpenMaya.MScriptUtil()
        util.createFromDouble(rampTwistValue)
        quaternion = OpenMaya.MQuaternion(rampTwistValue, curveTangent)
        curveNormal = curveNormal.rotateBy(quaternion)
        curveBinormal = curveBinormal.rotateBy(quaternion)

        # normalize vectors
        curveNormal.normalize()
        curveTangent.normalize()
        curveBinormal.normalize()

        # apply rampScale
        curveNormal *= rampScaleValue * 4  # possible rang attribute
        curveTangent *= rampScaleValue * 4
        curveBinormal *= rampScaleValue * 4

        curvePoint = OpenMaya.MPoint()
        inputCurveMfn.getPointAtParam(curveParam, curvePoint)

        # create transformMatrix
        mMatrix = OpenMaya.MFloatMatrix()
        OpenMaya.MScriptUtil.createFloatMatrixFromList((curveTangent.x, curveTangent.y, curveTangent.z, 0.0,
                                                        curveNormal.x, curveNormal.y, curveNormal.z, 0.0,
                                                        curveBinormal.x, curveBinormal.y, curveBinormal.z, 0.0,
                                                        curvePoint.x, curvePoint.y, curvePoint.z, curvePoint.w), mMatrix)

        # set output Value
        outputMatrixTransformHandle.setMFloatMatrix(mMatrix)

        # Mark output as clean
        pDataBlock.setClean(pPlug)


# AETemplate
def loadAETemplateCallback(nodeName):
    AEpositionOnCurveTemplate(nodeName)

# documentation: http://help.autodesk.com/cloudhelp/2017/CHS/Maya-Tech-Docs/Commands/editorTemplate.html
class AEpositionOnCurveTemplate(pm.ui.AETemplate):
    def addControll(self, control, label=None, **kwargs):
        pm.ui.AETemplate.addControl(self, control, label=label, **kwargs)

    def beginLayout(self, name, collapse=True):
        pm.ui.AETemplate.beginLayout(self, name, collapse=collapse)

    def __init__(self, nodeName):
        super(AEpositionOnCurveTemplate, self).__init__(nodeName)
        self.thisNode = None
        node = pm.PyNode(nodeName)
        if node.type() == kPluginNodeName:

            for attr in pm.listAttr(nodeName):
                self.suppress(attr)
                logger.debug('suppress %s.%s' % (nodeName, attr))

            self.callCustom(self.showTitle, lambda: None)

            self.beginScrollLayout()
            self.beginLayout('General', collapse=False)

            annotation = 'testing annotation'
            # controlls

            self.addControll('PositionCurve', label='PositionCurve', annotation=annotation)

            self.endLayout()

            # custom button
            # ramp control
            self.beginLayout('RampControl', collapse=True)
            mel.eval('AEaddRampControl("%s.rampScaleAttr");' % nodeName)
            mel.eval('AEaddRampControl("%s.rampTwistAttr");' % nodeName)
            self.endLayout()
            # twistRampAttr


            # explanation: AE add button
            # call custom: newFunc, replaceFunc, *attrs
            self.callCustom(self.newButton, self.buttonUpdate, 'PositionCurve')

            self.endLayout()

            self.endScrollLayout()

    def newButton(self, nodeName):
        pm.rowLayout(numberOfColumns=3, adjustableColumn=1, columnWidth3=(80, 100, 100))
        self.showNewManip = pm.button(label='Edit Manip', command=lambda *args: self.buttonShowManip(nodeName))

    def buttonUpdate(self, attr):
        nodeName = pm.PyNode(attr).nodeName()
        self.showNewManip.setCommand(lambda *args: self.buttonShowManip(nodeName))

    def buttonShowManip(self, nodeName):
        pm.select(cl=True)
        pm.select(nodeName)
        pm.runtime.ShowManipulators()

    def showTitle(self):
        pm.text('Position On Curve v' + kPluginVersion, font='boldLabelFont')


# command
class positionOnCurveCommand(OpenMayaMPx.MPxCommand):
    def __init__(self):
        super(positionOnCurveCommand, self).__init__()
        self.mUndo = []

    @classmethod
    def cmdCreator(cls):
        return OpenMayaMPx.asMPxPtr(cls())

    def isUndoable(self):
        return True

    def undoIt(self):
        OpenMaya.MGlobal.displayInfo('Undo: instanceAlongCurveCommand\n')

        # undo queue reversed, undo first the las action
        for m in reversed(self.mUndo):
            m.undoIt()  # <- MDagModifier
            """
            Undoes all of the operations that have been given to this modifier.
            It is only valid to call this method after the doIt method has been called.
            """
    def doIt(self, argList):
        """
        create nodes and connect.
        use: select two objects:
            1/ nurbsCurve transform node
            2/ mesh transform node

        """
        # get selection
        list = OpenMaya.MSelectionList()
        OpenMaya.MGlobal.getActiveSelectionList(list)

        # check number objects selected
        if list.length() != 2:
            sys.stderr.write("Please select a curve and a shape")
            return

        # get curve dagpath
        curveDagPath = OpenMaya.MDagPath()
        list.getDagPath(0, curveDagPath)  # element 0 to curveDagPath
        curveDagPath.extendToShape()

        # get Mesh dag path
        shapeDagPath = OpenMaya.MDagPath()
        list.getDagPath(1, shapeDagPath)

        # check type, curveDagPath must be kNurbsCurve
        # we use the method hasFn from MObject to assure that
        if not (curveDagPath.node().hasFn(OpenMaya.MFn.kNurbsCurve)):
            sys.stderr.write("Please select a curve first")
            return

        # curve transform plug
        # first plug from arrayAttr .worldMatrix[0]
        curvePlug = OpenMaya.MFnDagNode(curveDagPath).findPlug('worldSpace', False).elementByLogicalIndex(0)

        # shape transform too
        transformFn = OpenMaya.MFnDagNode(shapeDagPath)

        # create positionOnCurve Node
        mdagModifier = OpenMaya.MDagModifier()
        self.mUndo.append(mdagModifier)
        posOnCurveTransform = mdagModifier.createNode(kPluginNodeId)  # kPluginNodeId
        mdagModifier.doIt()
        posOnCurveTransformFn = OpenMaya.MFnDagNode(posOnCurveTransform)
        posOnCurveTransformFn.setName('positionOnCurve#')

        # create a transform node for PositionOnCurve
        # posOnCurveTransformFn.setName('positionOnCurveLocator#')

        # get locator shape
        nodeShapeDagPath = OpenMaya.MDagPath()
        posOnCurveTransformFn.getPath(nodeShapeDagPath)
        nodeShapeDagPath.extendToShape()
        nodeShapeFN = OpenMaya.MFnDagNode(nodeShapeDagPath)

        # need to create a decomposeMatrix node
        mdgModifier = OpenMaya.MDGModifier()
        self.mUndo.append(mdgModifier)
        decomposeMatrixHandle = mdgModifier.createNode('decomposeMatrix')
        mdgModifier.doIt()
        decomposeMatrixFn = OpenMaya.MFnDependencyNode(decomposeMatrixHandle)

        # todo: function with this
        # default values Ramp Attribute, if not the plug give errors on start
        defaultPosition = OpenMaya.MFloatArray(1, 0.0)
        defaultValues = OpenMaya.MFloatArray(1, 0.25)
        defaultInterpolations = OpenMaya.MIntArray(1, 3)
        plug = nodeShapeFN.findPlug(positionOnCurve.rampScaleAttr)
        ramp = OpenMaya.MRampAttribute(plug)
        ramp.addEntries(defaultPosition, defaultValues, defaultInterpolations)
        # rampTwistAttr
        defaultValues = OpenMaya.MFloatArray(1, 0.5)
        plug = nodeShapeFN.findPlug(positionOnCurve.rampTwistAttr)
        ramp = OpenMaya.MRampAttribute(plug)
        ramp.addEntries(defaultPosition, defaultValues, defaultInterpolations)

        # connect Nodes
        mdgModifier = OpenMaya.MDGModifier()
        self.mUndo.append(mdgModifier)
        # curve -> positionOnCurve Node
        mdgModifier.connect(curvePlug, nodeShapeFN.findPlug(positionOnCurve.inputCurveAttribute))
        # positionOnCurve -> decomposeMatrix
        mdgModifier.connect(nodeShapeFN.findPlug(positionOnCurve.outputMatrixTransformAttribute), decomposeMatrixFn.findPlug('inputMatrix', False))
        # decomposeMatrix -> mesh transform
        mdgModifier.connect(decomposeMatrixFn.findPlug('outputTranslate', False), transformFn.findPlug('translate', False))
        mdgModifier.connect(decomposeMatrixFn.findPlug('outputRotate', False), transformFn.findPlug('rotate', False))
        mdgModifier.connect(decomposeMatrixFn.findPlug('outputScale', False), transformFn.findPlug('scale', False))
        mdgModifier.doIt()

        # select positionOnCurve Node
        cmds.select(clear=True)
        cmds.select(posOnCurveTransformFn.name())
        # Open AE
        mel.eval('openAEWindow')


# manip
class positionOnCurveManip(OpenMayaMPx.MPxManipContainer):
    def __init__(self):
        super(positionOnCurveManip, self).__init__()
        self.nodeFn = OpenMaya.MFnDependencyNode()

    @classmethod
    def nodeCreator(cls):
        return OpenMayaMPx.asMPxPtr(cls())

    @staticmethod
    def nodeInitializer():
        OpenMayaMPx.MPxManipContainer.initialize()

    def createChildren(self):
        """
        Create Manipulator when positionOnCurve is selected
        """
        list = OpenMaya.MSelectionList()
        OpenMaya.MGlobal.getActiveSelectionList(list)
        self.distManip = None

        # no more than one object selected
        if list.length() != 1:
            return None

        self.distManip = self.addDistanceManip('positionManip', 'PositionCurve')

    def connectToDependNode(self, node):
        self.nodeFn.setObject(node)
        # input curve plug

        curvePositionPlug = self.nodeFn.findPlug(positionOnCurve.curvePositionAttribute)
        curvePlug = self.nodeFn.findPlug(positionOnCurve.inputCurveAttribute)

        connections = OpenMaya.MPlugArray()
        curvePlug.connectedTo(connections, True, False)
        curveNodeFn = OpenMaya.MFnDagNode(connections[0].node())
        curveNode = OpenMaya.MDagPath()
        curveNodeFn.getPath(curveNode)

        curveFn = OpenMaya.MFnNurbsCurve(curveNode)
        manipPos = OpenMaya.MPoint()
        curveFn.getPointAtParam(0.001, manipPos, OpenMaya.MSpace.kWorld)

        # get curve position plug
        # and set manip translation
        distanceManipFn = OpenMayaUI.MFnDistanceManip(self.distManip)
        distanceManipFn.setDirection(OpenMaya.MVector(0, 1, 0))
        distanceManipFn.connectToDistancePlug(curvePositionPlug)
        distanceManipFn.setTranslation(OpenMaya.MVector(manipPos), OpenMaya.MSpace.kWorld)
        mscriptutil = OpenMaya.MScriptUtil()

        # scale Manip
        mscriptutil.createFromList([10, 10, 10], 3)
        scaleDoubleArrayPtr = mscriptutil.asDoublePtr()

        distanceManipFn.setScale(scaleDoubleArrayPtr)

        self.finishAddingManips()
        OpenMayaMPx.MPxManipContainer.connectToDependNode(self, node)


def initializePlugin(plugin):
    pluginFn = OpenMayaMPx.MFnPlugin(plugin, 'Jap3D', kPluginVersion)
    try:
        # register node, don't miss OpenMayaMPx.MPxNode.kLocatorNode!!!
        pluginFn.registerNode(kPluginNodeName, kPluginNodeId, positionOnCurve.creator, positionOnCurve.nodeInitializer,
                              OpenMayaMPx.MPxNode.kLocatorNode)

        # register command, no initialize need for commands
        pluginFn.registerCommand(kPluginNodeNameCommand, positionOnCurveCommand.cmdCreator)

        # register AE template
        pm.callbacks(addCallback=loadAETemplateCallback, hook='AETemplateCustomContent', owner=kPluginNodeName)

        # register manip
        pluginFn.registerNode(kPluginNodeNameManip, kPluginNodeNameManipId, positionOnCurveManip.nodeCreator,
                              positionOnCurveManip.nodeInitializer, OpenMayaMPx.MPxNode.kManipContainer)

    except:
        sys.stderr.write('Failed to register node: ' + kPluginNodeName)
        raise

def uninitializePlugin(plugin):
    pluginFn = OpenMayaMPx.MFnPlugin(plugin)
    try:
        pluginFn.deregisterNode(kPluginNodeId)
        pluginFn.deregisterCommand(kPluginNodeNameCommand)
        pluginFn.deregisterNode(kPluginNodeNameManipId)

        pm.callbacks(removeCallback=loadAETemplateCallback, hook='AETemplateCustomContent', owner=kPluginNodeName)

    except:
        sys.stderr.write('Failed to deregister node: ' + kPluginNodeName)
        raise



#######
#UTILS#
#######
def getSingleSourceObjectFromPlug(plug):
    if plug.isConnected():
        # Get connected input plugs
        connections = OpenMaya.MPlugArray()
        plug.connectedTo(connections, True, False)

        # Find input transform
        if connections.length() == 1:
            return connections[0].node()

    return None

def getFnFromPlug(plug, fnType):
    node = getSingleSourceObjectFromPlug(plug)

    # Get Fn from a DAG path to get the world transformations correctly
    if node is not None:
        path = OpenMaya.MDagPath()
        trFn = OpenMaya.MFnDagNode(node)
        trFn.getPath(path)

        path.extendToShape()

        if path.node().hasFn(fnType):
            return path

    return None