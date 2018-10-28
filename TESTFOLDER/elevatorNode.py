from __future__ import division
"""
elevator node:
makes duplicate objetcs between two transforms. with a scissor pattern
"""
# todo: assign Shading group

import sys
import math
import maya.OpenMaya as OpenMaya
import maya.OpenMayaUI as OpenMayaUI
import maya.OpenMayaMPx as OpenMayaMPx
import traceback  # TODO: read about this

import math
import pymel.core as pm
import maya.cmds as cmds
import maya.mel as mel

import logging
logging.basicConfig()
logger = logging.getLogger('Elevator node:')
logger.setLevel(logging.INFO)

# documentation: https://help.autodesk.com/view/MAYAUL/2018/ENU/?guid=__files_GUID_AABB9BB4_816F_4C7C_A526_69B0568E1587_htm
# documentation: https://help.autodesk.com/view/MAYAUL/2018/ENU/?guid=__files_GUID_767D6572_552D_4D94_90E2_AE626F276D37_htm
# documentation: https://help.autodesk.com/view/MAYAUL/2018/ENU/?guid=__files_GUID_C5A68952_EB7D_41CC_ABF5_CC4C63293EED_htm
# documentation: https://stackoverflow.com/questions/50365958/maya-mpxnode-multiple-outputs

# Todo: more functionalities with manips
# TODO: add files count?

kPluginVersion = "0.0"
kPluginNodeName = 'elevatorLocator'
# identifier of the node
kPluginNodeId = OpenMaya.MTypeId(0x30049)
kPluginNodeClassify = 'utility/general'
kPluginNodeNameManip = 'elevatorManip'
kPluginNodeNameManipId = OpenMaya.MTypeId(0x30050)
kPluginNodeNameCommand = 'elevatorCommand'
kPluginNodeClassify = 'utility/general'  # not in use

kCallbackID = None

# we use the maya locator proxy as base class for our node.
# So we can look our node in the outliner
class elevatorNode(OpenMayaMPx.MPxLocatorNode):
    # define inputs
    # input transform matrix and msg. message useful for track the object
    inputMatrix01Attribute = OpenMaya.MObject()
    inputMatrix02Attribute = OpenMaya.MObject()

    # repeteable object
    inputObjectMsgAttribute = OpenMaya.MObject()

    # value attr
    numFloorAttribute = OpenMaya.MObject()
    lengthStickAttribute = OpenMaya.MObject()

    # define outputs
    outputMatrixTransformAttribute = OpenMaya.MObject()

    @classmethod
    def creator(cls):
        # node creator for classic python API
        return OpenMayaMPx.asMPxPtr(cls())

    @staticmethod
    def nodeInitializer():
        # associate node with its manipulator
        # OpenMayaMPx.MPxManipContainer.addToManipConnectTable(kPluginNodeId)

        # To make things more readable
        node = elevatorNode

        # create attributes
        matrixAttrFn = OpenMaya.MFnMatrixAttribute()
        mfnAttr = OpenMaya.MFnNumericAttribute()
        msgAttributeFn = OpenMaya.MFnMessageAttribute()

        # inputMatrixAttr01
        node.inputMatrix01Attribute = matrixAttrFn.create('Matrix01', 'Matrix01', OpenMaya.MFnNumericData.kDouble)
        node.addAttribute(node.inputMatrix01Attribute)

        # inputMatrixAttr02
        node.inputMatrix02Attribute = matrixAttrFn.create('Matrix02', 'Matrix02', OpenMaya.MFnNumericData.kDouble)
        node.addAttribute(node.inputMatrix02Attribute)

        # RepeatableObject
        node.inputObjectMsgAttribute = msgAttributeFn.create('Object', 'Object')
        node.addAttribute(node.inputObjectMsgAttribute)

        # num floor
        node.numFloorAttribute = mfnAttr.create('NumFloor', 'NumFloor', OpenMaya.MFnNumericData.kInt, 3)
        mfnAttr.setMin(1)
        mfnAttr.setSoftMax(20)
        mfnAttr.setChannelBox(False)
        mfnAttr.setConnectable(False)
        node.addAttribute(node.numFloorAttribute)

        # length stick
        node.lengthStickAttribute = mfnAttr.create('Length', 'Length', OpenMaya.MFnNumericData.kDouble, 10.0)
        mfnAttr.setMin(3.0)
        mfnAttr.setSoftMax(500.0)
        mfnAttr.setChannelBox(False)
        mfnAttr.setConnectable(False)
        node.addAttribute(node.lengthStickAttribute)

        # output
        node.outputMatrixTransformAttribute = matrixAttrFn.create('outTransform', 'outTransform', OpenMaya.MFnNumericData.kDouble)
        matrixAttrFn.setKeyable(False)
        matrixAttrFn.setStorable(True)
        matrixAttrFn.setReadable(True)
        matrixAttrFn.setWritable(False)
        matrixAttrFn.setHidden(False)
        matrixAttrFn.setArray(True)
        matrixAttrFn.setUsesArrayDataBuilder(True)  # review: setUsesArrayDataBuilder
        matrixAttrFn.setDisconnectBehavior(OpenMaya.MFnAttribute.kDelete)  # nothing connected, remove attr
        node.addAttribute(node.outputMatrixTransformAttribute)


        # define attributes relations to update
        node.attributeAffects(node.inputMatrix01Attribute, node.outputMatrixTransformAttribute)
        node.attributeAffects(node.inputMatrix02Attribute, node.outputMatrixTransformAttribute)
        node.attributeAffects(node.numFloorAttribute, node.outputMatrixTransformAttribute)
        node.attributeAffects(node.lengthStickAttribute, node.outputMatrixTransformAttribute)


        return True

    def __init__(self):
        # return to super
        OpenMayaMPx.MPxLocatorNode.__init__(self)

    def postConstructor(self):
        global kCallbackID
        # here will launch callbacks
        # documentation: MNodeMessage: https://help.autodesk.com/view/MAYAUL/2018/ENU/?guid=__cpp_ref_class_m_node_message_html
        OpenMaya.MFnDependencyNode(self.thisMObject()).setName('elevatorLocatorShape')
        kCallbackID = OpenMaya.MNodeMessage.addAttributeChangedCallback(self.thisMObject(), self.attrChangeCallback)
        self.updateInstanceConnections()

    def attrChangeCallback(self, msg, plug, otherPlug, clientData):
        """
            msg: the kind of attribute CHANGE triggering the callback,
                pe. if attribute is disconnected, modified, connected, etc
            plug: the node's plug where the connection changed (mPlug)
            otherPlug: the plug opposite the node's plug where the connection changed
            clientData: User defined data passed to the callback function
        """
        logger.debug('--Callback--')
        # check DATA
        # kIncomingDirection: the connection was coming into the node
        incomingDirection = (OpenMaya.MNodeMessage.kIncomingDirection & msg) == OpenMaya.MNodeMessage.kIncomingDirection
        # kAttributeSet: an attribute value of this node has been set
        attributeSet = (OpenMaya.MNodeMessage.kAttributeSet & msg) == OpenMaya.MNodeMessage.kAttributeSet

        # check if attribute is numFloorAttribute
        isCorrectAttribute = (plug.attribute() == self.numFloorAttribute)

        # check if is correct Node
        isCorrectNode = OpenMaya.MFnDependencyNode(plug.node()).typeName() == kPluginNodeName

        try:
            if incomingDirection and attributeSet and isCorrectAttribute and isCorrectNode:
                # we need to separate in other func, so we can launch separately of the callback
                self.updateInstanceConnections()
        except:
            sys.stderr.write('Failed trying to update instances. stack trace: \n')
            sys.stderr.write(traceback.format_exc())


    def updateInstanceConnections(self):
        # fixme: infinite bucle
        # a callback manage this
        # If the locator is being instanced, just stop updating its children.
        # This is to prevent losing references to the locator instances' children
        # If you want to change this locator, prepare the source before instantiating
        # Explanation: ask if is an instance, from MObject
        if OpenMaya.MFnDagNode(self.thisMObject()).isInstanced():
            return OpenMaya.kUnknownParameter  # review: learn about this

        logger.debug('--Callback.updateInstanceConnections--')
        expectedInstancesCountPlug = OpenMaya.MPlug(self.thisMObject(), self.numFloorAttribute)
        expectedInstancesCount = expectedInstancesCountPlug.asInt()
        logger.debug('expected Instances Count : %s' % expectedInstancesCount)

        # plugs
        outputMatrixTransformPlug = OpenMaya.MPlug(self.thisMObject(), self.outputMatrixTransformAttribute)
        numConnectedElements = outputMatrixTransformPlug.numConnectedElements()
        logger.debug('num connected elements: %s' % numConnectedElements)

        # check how many elements we have connected
        if numConnectedElements < expectedInstancesCount:  # create necessary elements
            # get the repeatable object
            inputTransformPlug = OpenMaya.MPlug(self.thisMObject(), self.inputObjectMsgAttribute)
            connections = OpenMaya.MPlugArray()
            inputTransformPlug.connectedTo(connections, True, False)
            # fixme: possible empty array, try or check length
            if not connections.length():
                return

            inputTransformFn = OpenMaya.MFnTransform(connections[0].node())  # get transform Fn from the plug

            # get shadingGroup from input mesh, we need the shape
            inputMeshDPath = OpenMaya.MDagPath()
            inputTransformFn.getPath(inputMeshDPath)  # get DAG PATH
            inputMeshDPath.extendToShape()  # get shape
            inputMeshFn = OpenMaya.MFnDagNode(inputMeshDPath)
            shGrpPlugArray = inputMeshFn.findPlug('instObjGroups', False)
            shGrpPlug = shGrpPlugArray.elementByLogicalIndex(0)

            sgGrpArrayDestinations = OpenMaya.MPlugArray()
            shGrpPlug.connectedTo(sgGrpArrayDestinations, False, True)
            shGrpFn = OpenMaya.MFnSet(sgGrpArrayDestinations[0].node())

            if inputTransformFn is not None:
                # get elevatorNode TRANSFORM transformFn
                dagNode = OpenMaya.MFnDagNode(self.thisMObject())
                dagPath = OpenMaya.MDagPath()
                dagNode.getPath(dagPath)
                # elevatorLocator transform node MFnTransform
                elevatorTransformMFnTr = OpenMaya.MFnTransform(dagPath.transform())

                # number of new instances
                newInstances = expectedInstancesCount - numConnectedElements
                # find available indices, first check actual indices
                totalIndexArray = OpenMaya.MIntArray()

                # booth connected and disconnected
                outputMatrixTransformPlug.getExistingArrayAttributeIndices(totalIndexArray)
                # actual available index, filter connected plugs
                availableIndex = {i for i in totalIndexArray if not outputMatrixTransformPlug.elementByPhysicalIndex(i).isConnected()}
                # check how many elements we need and how many we have free
                necessaryNewIndex = newInstances - len(availableIndex)
                # if we need more free index
                if necessaryNewIndex > 0:
                    if not len(availableIndex):
                        availableIndex.add((totalIndexArray.length()))
                    maxIndex = (max(availableIndex))  # highest value
                    for i in range(necessaryNewIndex):
                        availableIndex.add(maxIndex+i)

                # if we have to much free index
                if necessaryNewIndex < 0:
                    for i in range(necessaryNewIndex, 0):
                        availableIndex.remove(max(availableIndex))

                logger.debug('available indices : %s' % availableIndex)
                # here duplicate and connect new instances
                mDGModifier = OpenMaya.MDGModifier()

                for i in availableIndex:
                    logger.debug('index operating: %s' % i)
                    # instance transform
                    # InstanceLeaf must be set to False to prevent crash
                    trInstance = inputTransformFn.duplicate(True, False)  # duplicate instanced
                    instanceFn = OpenMaya.MFnTransform(trInstance)

                    # parent new instance
                    elevatorTransformMFnTr.addChild(trInstance)

                    # MDgModifier to create decompose matrix
                    decomposeMatrix = mDGModifier.createNode('decomposeMatrix')
                    decomposeMatrixFn = OpenMaya.MFnDependencyNode(decomposeMatrix)

                    # connect elevator to decomposematrix
                    mDGModifier.connect(outputMatrixTransformPlug.elementByLogicalIndex(i),
                                        decomposeMatrixFn.findPlug('inputMatrix', False))

                    # connect matrix to instance
                    mDGModifier.connect(decomposeMatrixFn.findPlug('outputTranslate', False),
                                        instanceFn.findPlug('translate'))
                    mDGModifier.connect(decomposeMatrixFn.findPlug('outputRotate', False),
                                        instanceFn.findPlug('rotate'))

                # apply shadingGrp and execute
                mDGModifier.commandToExecute('sets -e -nw -fe ' + shGrpFn.name() + ' ' + elevatorTransformMFnTr.name())
                mDGModifier.doIt()

        # delete necessary elements
        elif numConnectedElements > expectedInstancesCount:
            connections = OpenMaya.MPlugArray()
            toRemove = numConnectedElements - expectedInstancesCount
            mDGModifier = OpenMaya.MDGModifier()
            logger.debug('remove num: %s' % toRemove)

            for i in range(toRemove):
                outputTransformPlugElement = outputMatrixTransformPlug.connectionByPhysicalIndex(numConnectedElements-1-i)
                outputTransformPlugElement.connectedTo(connections, False, True)
                logger.debug('prepare for deleting: %s' % connections.length())

                for c in range(connections.length()):
                    # review: if is necessary track from decomposeMatrix
                    decomposeMatrixNode = connections[c].node()
                    mFnDG = OpenMaya.MFnDependencyNode(decomposeMatrixNode)
                    decomposeOutPlug = mFnDG.findPlug('outputTranslate', False)
                    arrayDestinationsPlug = OpenMaya.MPlugArray()
                    decomposeOutPlug.connectedTo(arrayDestinationsPlug, False, True)

                    logger.debug('removing: %s, %s' % (mFnDG.name(), OpenMaya.MFnDependencyNode(arrayDestinationsPlug[0].node()).name()))
                    mDGModifier.deleteNode(decomposeMatrixNode)
                    mDGModifier.deleteNode(arrayDestinationsPlug[0].node())

            mDGModifier.doIt()


    def isBounded(self):
        return True

    def boundingBox(self):
        return OpenMaya.MBoundingBox(OpenMaya.MPoint(-1, -1, -1), OpenMaya.MPoint(1, 1, 1))

    # plug represents output attribute
    # dataBlock all values
    def compute(self, pPlug, pDataBlock):
        # node behavior
        # check outputs
        if pPlug == elevatorNode.outputMatrixTransformAttribute:
            logger.debug('__COMPUTE__')
            # get Data handles
            # num Floors
            numFloorHandle = pDataBlock.inputValue(elevatorNode.numFloorAttribute)
            numFloor = numFloorHandle.asInt()
            # stick length
            lengthStickHandle = pDataBlock.inputValue(elevatorNode.lengthStickAttribute)
            lengthStick = lengthStickHandle.asDouble()

            # inputMatrixTransforms
            inputMatrix01Handle = pDataBlock.inputValue(elevatorNode.inputMatrix01Attribute)
            inputMatrix01Attribute = inputMatrix01Handle.asFloatMatrix()
            inputMatrix02Handle = pDataBlock.inputValue(elevatorNode.inputMatrix02Attribute)
            inputMatrix02Attribute = inputMatrix02Handle.asFloatMatrix()

            # set ouputTransformMatrix
            # get output
            outputMatrixTransformHandle = pDataBlock.outputArrayValue(elevatorNode.outputMatrixTransformAttribute)

            # get distance vector, position im01 - im02
            # Explanation: this way we don't need mscriptUtils
            distanceVector = OpenMaya.MVector(inputMatrix02Attribute(3, 0) - inputMatrix01Attribute(3, 0),
                                              inputMatrix02Attribute(3, 1) - inputMatrix01Attribute(3, 1),
                                              inputMatrix02Attribute(3, 2) - inputMatrix01Attribute(3, 2))

            floorVector = distanceVector / numFloor

            # calculate angle, length of stick object must touch the upper floor
            # we can use pitagoras theorem
            # floorVector -> C
            # ? = -> c
            # lengthStick -> H:   H^2 = c^2 + C^2 ::::> H^2 - C^2 = c^2

            baseLength = (lengthStick**2 - (floorVector.length())**2)**0.5
            # cosinus => H / c
            cosinus = baseLength / lengthStick
            angle = math.acos(cosinus)  # radians

            # calculate vectors
            xVector = OpenMaya.MVector(inputMatrix01Attribute(0,0), inputMatrix01Attribute(0,1), inputMatrix01Attribute(0,2))
            zVector = xVector ^ floorVector
            # todo: maybe recalculate cross product X

            # rotateVectors
            quaternion = OpenMaya.MQuaternion(angle, zVector)
            xVector = xVector.rotateBy(quaternion)
            yVector = OpenMaya.MVector(floorVector)

            # Normaliza lengths
            xVector.normalize()
            zVector.normalize()
            yVector.normalize()


            for i in range(numFloor):

                util = OpenMaya.MScriptUtil()
                mFloatMatrix = OpenMaya.MFloatMatrix()
                logger.debug('Per floor value: %s,%s,%s' % (floorVector.x * (i + 1), floorVector.y*(i + 1), floorVector.z*(i + 1)))

                util.createFloatMatrixFromList([xVector.x,xVector.y,xVector.z,0,
                                                yVector.x,yVector.y,yVector.z,0,
                                                zVector.x,zVector.y,zVector.z,0,
                                                floorVector.x * i + inputMatrix01Attribute(3, 0),
                                                floorVector.y * i + inputMatrix01Attribute(3, 1),
                                                floorVector.z * i + inputMatrix01Attribute(3, 2), 1], mFloatMatrix)

                try:
                    outputMatrixTransformHandle.jumpToArrayElement(i)
                    outputIndexHandle = outputMatrixTransformHandle.outputValue()

                    # set output
                    outputIndexHandle.setMFloatMatrix(mFloatMatrix)
                    outputIndexHandle.setClean()
                except:
                    return OpenMaya.kUnknownParameter

            logger.debug('__End COMPUTE__')
            outputMatrixTransformHandle.setAllClean()
            outputMatrixTransformHandle.setClean()
            pDataBlock.setClean(pPlug)

        else:
            sys.stderr.write('Failed trying to compute locator. stack trace: \n')
            sys.stderr.write(traceback.format_exc())
            return OpenMaya.kUnknownParameter

        return True

def initializePlugin(plugin):
    pluginFn = OpenMayaMPx.MFnPlugin(plugin, 'Jap3D', kPluginVersion)
    try:
        # register node, don't miss OpenMayaMPx.MPxNode.kLocatorNode!!!
        pluginFn.registerNode(kPluginNodeName, kPluginNodeId, elevatorNode.creator, elevatorNode.nodeInitializer,
                              OpenMayaMPx.MPxNode.kLocatorNode)

        # register command, no initialize need for commands
        # pluginFn.registerCommand(kPluginNodeNameCommand, positionOnCurveCommand.cmdCreator)

        # register AE template
        # pm.callbacks(addCallback=loadAETemplateCallback, hook='AETemplateCustomContent', owner=kPluginNodeName)

        # register manip
        # pluginFn.registerNode(kPluginNodeNameManip, kPluginNodeNameManipId, positionOnCurveManip.nodeCreator,
        #                       positionOnCurveManip.nodeInitializer, OpenMayaMPx.MPxNode.kManipContainer)

    except:
        sys.stderr.write('Failed to register node: ' + kPluginNodeName)
        raise


def uninitializePlugin(plugin):
    pluginFn = OpenMayaMPx.MFnPlugin(plugin)
    try:
        pluginFn.deregisterNode(kPluginNodeId)
        OpenMaya.MNodeMessage.removeCallback(kCallbackID)
        # pluginFn.deregisterCommand(kPluginNodeNameCommand)
        # pluginFn.deregisterNode(kPluginNodeNameManipId)

        # pm.callbacks(removeCallback=loadAETemplateCallback, hook='AETemplateCustomContent', owner=kPluginNodeName)

    except:
        sys.stderr.write('Failed to deregister node: ' + kPluginNodeName)
        raise


########
# UTILS#
########
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