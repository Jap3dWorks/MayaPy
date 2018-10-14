import sys

import maya.OpenMaya as OpenMaya
import maya.OpenMayaUI as OpenMayaUI
import maya.OpenMayaMPx as OpenMayaMPx

import pymel.core as pm
import maya.cmds as cmds
import maya.mel as mel

# documentation: https://help.autodesk.com/view/MAYAUL/2018/ENU/?guid=__files_GUID_AABB9BB4_816F_4C7C_A526_69B0568E1587_htm
# documentation: https://help.autodesk.com/view/MAYAUL/2018/ENU/?guid=__files_GUID_767D6572_552D_4D94_90E2_AE626F276D37_htm
# documentation: https://help.autodesk.com/view/MAYAUL/2018/ENU/?guid=__files_GUID_C5A68952_EB7D_41CC_ABF5_CC4C63293EED_htm
# documentation: https://stackoverflow.com/questions/50365958/maya-mpxnode-multiple-outputs

# TODO: Manip position enhancements: change position, change range
# TODO: AE TEMPLATE

kPluginVersion = "0.0"
kPluginNodeName = 'positionOnCurve'
# identifier of the node
kPluginNodeId = OpenMaya.MTypeId(0x010fff)
kPluginNodeClassify = 'utility/general'
kPluginNodeNameManip = 'positionOnCurveManip'
kPluginNodeNameManipId = OpenMaya.MTypeId(0x010ff9)
kPluginNodeNameCommand = 'positionOnCurveCommand'

# we use the maya proxy as base class for our node
class positionOnCurve(OpenMayaMPx.MPxLocatorNode):
    # define inputs
    inputCurveAttribute = OpenMaya.MObject()
    curvePositionAttribute = OpenMaya.MObject()
    rampScaleAttr = OpenMaya.MObject()
    manipAttr = OpenMaya.MObject()
    # define outputs
    outputMatrixTransformAttribute = OpenMaya.MObject()

    @classmethod
    def creator(cls):
        # Explanation: node creator for classic python API
        return OpenMayaMPx.asMPxPtr(cls())

    @staticmethod
    def initialize():
        # associate node with its manipulator
        OpenMayaMPx.MPxManipContainer.addToManipConnectTable(kPluginNodeId)

        # To make things more readable
        node = positionOnCurve

        # ManipAttr
        mfnAttr = OpenMaya.MFnNumericAttribute()
        # documentation: https://help.autodesk.com/view/MAYAUL/2018/ENU/?guid=__cpp_ref_class_m_fn_distance_manip_html
        # Explanation: data type corresponding to distanceManip is a double
        node.manipAttr = mfnAttr.create('ManipValue', 'MV', OpenMaya.MFnNumericData.kDouble)
        mfnAttr.setHidden(False)
        node.addAttribute(node.manipAttr)

        # create attributes
        mfnAttr = OpenMaya.MFnNumericAttribute()

        # Ramp attribute
        rampAttrFn = OpenMaya.MRampAttribute()
        node.rampScaleAttr = rampAttrFn.createCurveRamp('curveRamp', 'curveRamp')

        node.addAttribute(node.rampScaleAttr)

        # positionAttr
        node.curvePositionAttribute = mfnAttr.create('Position', 'p', OpenMaya.MFnNumericData.kDouble, 0.5)
        mfnAttr.setKeyable(True)
        mfnAttr.setStorable(True)
        mfnAttr.setReadable(False)
        mfnAttr.setWritable(True)
        mfnAttr.setMin(0.0)
        mfnAttr.setMax(1.0)

        # transformationAttr
        mfnAttr = OpenMaya.MFnMatrixAttribute()
        node.outputMatrixTransformAttribute = mfnAttr.create('Transformation', 't', 0)  # 1 double precision
        mfnAttr.setKeyable(False)
        mfnAttr.setStorable(True)
        mfnAttr.setReadable(True)
        mfnAttr.setWritable(False)
        mfnAttr.setHidden(False)

        # curveAttr
        mfnAttr = OpenMaya.MFnTypedAttribute()
        node.inputCurveAttribute = mfnAttr.create('Curve', 'c', 16)
        mfnAttr.setKeyable(False)
        mfnAttr.setStorable(False)
        mfnAttr.setReadable(False)
        mfnAttr.setWritable(True)
        mfnAttr.setHidden(False)

        # attach attributes
        node.addAttribute(node.curvePositionAttribute)
        node.addAttribute(node.inputCurveAttribute)
        node.addAttribute(node.outputMatrixTransformAttribute)

        # define attributes relations to update
        node.attributeAffects(node.inputCurveAttribute, node.outputMatrixTransformAttribute)
        node.attributeAffects(node.curvePositionAttribute, node.outputMatrixTransformAttribute)

        # rampAttr
        node.attributeAffects(node.rampScaleAttr, node.outputMatrixTransformAttribute)

    def __init__(self):
        super(positionOnCurve, self).__init__()

    def isBounded(self):
        return True

    def boundingBox(self):
        return OpenMaya.MBoundingBox(OpenMaya.MPoint(-1, -1, -1), OpenMaya.MPoint(1, 1, 1))

    # plug represents output attribute
    # dataBlock all values
    def compute(self, pPlug, pDataBlock):
        # TODO: add twist
        if pPlug != self.outputMatrixTransformAttribute:  # Review: self.
            return None

        # obtain data handles for each attribute and values
        inputCurveHandle = pDataBlock.inputValue(positionOnCurve.inputCurveAttribute)  # get mDataHandle
        inputCurve = inputCurveHandle.asNurbsCurveTransformed()  # mObject

        curvePositionHandle = pDataBlock.inputValue(positionOnCurve.curvePositionAttribute)  # get mDataHandle
        curvePosition = curvePositionHandle.asDouble()  # asDouble

        # obtain outputHandle
        outputMatrixTransformHandle = pDataBlock.outputValue(positionOnCurve.outputMatrixTransformAttribute)  # get mDataHandle

        # compute
        # create curves fn
        inputCurveMfn = OpenMaya.MFnNurbsCurve(inputCurve)
        # TODO: search dag node
        curveLenght = inputCurveMfn.length()

        pointPosition = curvePosition * curveLenght
        curveParam = inputCurveMfn.findParamFromLength(pointPosition)
        curveNormal = inputCurveMfn.normal(max(curveParam - 0.001, 0.001))

        curveTangent = inputCurveMfn.tangent(curveParam)
        curveBinormal = curveTangent ^ curveNormal
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
            m.undoIt()  # <- MDGModifier
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
        mdgModifier = OpenMaya.MDGModifier()
        self.mUndo.append(mdgModifier)
        positionOnCurveNode = mdgModifier.createNode(kPluginNodeId)
        mdgModifier.doIt()
        positionOnCurveNodeFn = OpenMaya.MFnDependencyNode(positionOnCurveNode)

        # need to create a decomposeMatrix node
        mdgModifier = OpenMaya.MDGModifier()
        self.mUndo.append(mdgModifier)
        decomposeMatrixHandle = mdgModifier.createNode('decomposeMatrix')
        mdgModifier.doIt()
        decomposeMatrixFn = OpenMaya.MFnDependencyNode(decomposeMatrixHandle)

        # connect Nodes
        mdgModifier = OpenMaya.MDGModifier()
        self.mUndo.append(mdgModifier)
        # curve -> positionOnCurve
        mdgModifier.connect(curvePlug, positionOnCurveNodeFn.findPlug(positionOnCurve.inputCurveAttribute, False))
        # positionOnCurve -> decomposeMatrix
        mdgModifier.connect(positionOnCurveNodeFn.findPlug(positionOnCurve.outputMatrixTransformAttribute), decomposeMatrixFn.findPlug('inputMatrix', False))
        # decomposeMatrix -> mesh transform
        mdgModifier.connect(decomposeMatrixFn.findPlug('outputTranslate', False), transformFn.findPlug('translate', False))
        mdgModifier.connect(decomposeMatrixFn.findPlug('outputRotate', False), transformFn.findPlug('rotate', False))
        mdgModifier.doIt()

        # select positionOnCurve Node
        cmds.select(clear=True)
        cmds.select(positionOnCurveNodeFn.name())
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

        # no more than one object selected
        if list.length() != 1:
            return None

        self.distManip = self.addDistanceManip('positionManip', 'position')

    def connectToDependNode(self, node):
        self.nodeFn.setObject(node)
        # input curve plug
        curvePlug = self.nodeFn.findPlug(positionOnCurve.curvePositionAttribute)

        # self.curveFn = OpenMaya.MFnNurbsCurve(getFnFromPlug(curvePlug, OpenMaya.MFn.kNurbsCurve))
        # maxParam = self.curveFn.findParamFromLength(self.curveFn.length())

        # get curve position plug
        # curvePositionPlug = self.curveFn.findPlug(positionOnCurve.curvePositionAttribute)

        # connect ont to one manip
        distanceManipFn = OpenMayaUI.MFnDistanceManip(self.distManip)
        distanceManipFn.setDirection(OpenMaya.MVector(0,1,0))
        distanceManipFn.connectToDistancePlug(curvePlug)

        # distanceIndex = distanceManipFn.distanceIndex()
        # print('distance index is: %s' % distanceIndex)
        # self.addPlugToManipConversion(distanceIndex)

        self.finishAddingManips()
        OpenMayaMPx.MPxManipContainer.connectToDependNode(self, node)


def initializePlugin(plugin):
    pluginFn = OpenMayaMPx.MFnPlugin(plugin, 'Jap3D', kPluginVersion)
    try:
        # register node
        pluginFn.registerNode(kPluginNodeName, kPluginNodeId, positionOnCurve.creator, positionOnCurve.initialize)
        # register command, no initialize need for commands
        pluginFn.registerCommand(kPluginNodeNameCommand, positionOnCurveCommand.cmdCreator)
        pluginFn.registerNode(kPluginNodeNameManip, kPluginNodeNameManipId, positionOnCurveManip.nodeCreator, positionOnCurveManip.nodeInitializer, OpenMayaMPx.MPxNode.kManipContainer)

    except:
        sys.stderr.write('Failed to register node: ' + kPluginNodeName)
        raise

def uninitializePlugin(plugin):
    pluginFn = OpenMayaMPx.MFnPlugin(plugin)
    try:
        pluginFn.deregisterNode(kPluginNodeId)
        pluginFn.deregisterCommand(kPluginNodeNameCommand)
        pluginFn.deregisterNode(kPluginNodeNameManipId)

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