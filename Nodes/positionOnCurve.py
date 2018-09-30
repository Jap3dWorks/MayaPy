import sys

import maya.api.OpenMaya as OpenMaya
# documentation: https://help.autodesk.com/view/MAYAUL/2018/ENU/?guid=__files_GUID_AABB9BB4_816F_4C7C_A526_69B0568E1587_htm
# documentation: https://help.autodesk.com/view/MAYAUL/2018/ENU/?guid=__files_GUID_767D6572_552D_4D94_90E2_AE626F276D37_htm
# documentation: https://help.autodesk.com/view/MAYAUL/2018/ENU/?guid=__files_GUID_C5A68952_EB7D_41CC_ABF5_CC4C63293EED_htm
# documentation: https://stackoverflow.com/questions/50365958/maya-mpxnode-multiple-outputs

def maya_useNewAPI():
    pass

kPluginNodeName = 'positionOnCurve'
# identifier of the node
kPluginNodeId = OpenMaya.MTypeId(0x010fff)

# we use the maya proxy as base class for our node
class positionOnCurve(OpenMaya.MPxNode):
    # define inputs
    inputCurveAttribute = OpenMaya.MObject()
    curvePositionAttribute = OpenMaya.MObject()
    # define outputs
    outputMatrixTransformAttribute = OpenMaya.MObject()

    @classmethod
    def creator(cls):
        # unlike openMaya 2, we need to return this as MPxPtr instead
        return cls()

    @staticmethod
    def initialize():
        # create attributes
        mfnAttr = OpenMaya.MFnNumericAttribute()

        # positionAttr
        positionOnCurve.curvePositionAttribute = mfnAttr.create('Position', 'p', OpenMaya.MFnNumericData.kFloat, 0.5)
        mfnAttr.keyable = True
        mfnAttr.storable = True
        mfnAttr.readable = False
        mfnAttr.writable = True
        mfnAttr.setMin(0.0)
        mfnAttr.setMax(1.0)

        # transformationAttr
        mfnAttr = OpenMaya.MFnMatrixAttribute()
        positionOnCurve.outputMatrixTransformAttribute = mfnAttr.create('Transformation', 't', 0)  # 1 double precision
        mfnAttr.keyable = False
        mfnAttr.storable = True
        mfnAttr.readable = True
        mfnAttr.writable = False
        mfnAttr.hidden = False

        # curveAttr
        mfnAttr = OpenMaya.MFnTypedAttribute()
        positionOnCurve.inputCurveAttribute = mfnAttr.create('Curve', 'c', 16)
        mfnAttr.keyable = False
        mfnAttr.storable = False
        mfnAttr.readable = False
        mfnAttr.writable = True
        mfnAttr.hidden = False

        # attach attributes
        positionOnCurve.addAttribute(positionOnCurve.curvePositionAttribute)
        positionOnCurve.addAttribute(positionOnCurve.inputCurveAttribute)
        positionOnCurve.addAttribute(positionOnCurve.outputMatrixTransformAttribute)

        # define attributes relations to update
        positionOnCurve.attributeAffects(positionOnCurve.inputCurveAttribute, positionOnCurve.outputMatrixTransformAttribute)
        positionOnCurve.attributeAffects(positionOnCurve.curvePositionAttribute, positionOnCurve.outputMatrixTransformAttribute)


    def __init__(self):
        super(positionOnCurve, self).__init__()

    # plug represents output attribute
    # dataBlock all inputs values
    def compute(self, pPlug, pDataBlock):
        if pPlug != positionOnCurve.outputMatrixTransformAttribute:
            return None

        # obtain data handles for each attribute and values
        inputCurveHandle = pDataBlock.inputValue(positionOnCurve.inputCurveAttribute)  # get mDataHandle
        inputCurve = inputCurveHandle.asNurbsCurve()  # mObject

        curvePositionHandle = pDataBlock.inputValue(positionOnCurve.curvePositionAttribute)  # get mDataHandle
        curvePosition = curvePositionHandle.asFloat()  #float

        # obtain outputHandle
        outputMatrixTransformHandle = pDataBlock.outputValue(positionOnCurve.outputMatrixTransformAttribute)  # get mDataHandle

        # compute
        # create curves fn
        inputCurveMfn = OpenMaya.MFnNurbsCurve(inputCurve)
        # TODO: search dag node
        inputCurveMfn.setObject(inputCurveMfn.getPath())  # set as dag path, to allow kworld transforms
        curveLenght = inputCurveMfn.length()

        pointPosition = curvePosition * curveLenght
        curveParam = inputCurveMfn.findParamFromLength(pointPosition)
        try:
            curveNormal = inputCurveMfn.normal(curveParam, OpenMaya.MSpace.kWorld)
        except:
            curveNormal = inputCurveMfn.normal(curveParam-0.001, OpenMaya.MSpace.kWorld) if not curvePosition == 0 else inputCurveMfn.normal(curveParam+0.001, OpenMaya.MSpace.kWorld)
        curveTangent = inputCurveMfn.tangent(curveParam, OpenMaya.MSpace.kWorld)
        curveBinormal = curveTangent ^ curveNormal
        curvePoint = inputCurveMfn.getPointAtParam(curveParam, OpenMaya.MSpace.kWorld)

        # create transformMatrix
        mMatrix = OpenMaya.MFloatMatrix(((curveTangent.x, curveTangent.y, curveTangent.z, 0.0),
                                         (curveNormal.x, curveNormal.y, curveNormal.z, 0.0),
                                         (curveBinormal.x, curveBinormal.y, curveBinormal.z, 0.0),
                                         (curvePoint.x, curvePoint.y, curvePoint.z, curvePoint.w)))

        # set output Value
        outputMatrixTransformHandle.setMFloatMatrix(mMatrix)

        # Mark output as clean
        pDataBlock.setClean(pPlug)



def initializePlugin(plugin):
    pluginFn = OpenMaya.MFnPlugin(plugin)
    try:
        pluginFn.registerNode(kPluginNodeName, kPluginNodeId, positionOnCurve.creator, positionOnCurve.initialize)
    except:
        sys.stderr.write('Failed to register node: ' + kPluginNodeName)
        raise

def uninitializePlugin(plugin):
    pluginFn = OpenMaya.MFnPlugin(plugin)
    try:
        pluginFn.deregisterNode(kPluginNodeId)
    except:
        sys.stderr.write('Failed to deregister node: ' + kPluginNodeName)
        raise

"""
from Nodes import positionOnCurve
# reload(positionOnCurve)
from maya import cmds
def connectPositionCurve():
    #list curves
    curveNode = cmds.ls(sl=True, type='nurbsCurve', dag=True)[0]
    #list shape
    meshNode = cmds.ls(sl=True, type='mesh', dag=True)[0]
    transformNode = cmds.listRelatives(meshNode, p=True)[0]
    
    # Force is important because of the undo stack
    try:
        cmds.unloadPlugin(positionOnCurve.__file__, force=True)
    finally:
        cmds.loadPlugin(positionOnCurve.__file__)
    
    positionOnCurveNode=cmds.createNode('positionOnCurve', name='positionOnCurve')
    decomposeMatrixNode=cmds.createNode('decomposeMatrix', name='decomposeMatrix')
    cmds.connectAttr('%s.Transformation' % positionOnCurveNode, '%s.inputMatrix' % decomposeMatrixNode)
    
    cmds.connectAttr('%s.worldSpace' % curveNode, '%s.Curve' % positionOnCurveNode)
    cmds.connectAttr('%s.outputTranslate' % decomposeMatrixNode, '%s.translate' % transformNode)
    cmds.connectAttr('%s.outputRotate' % decomposeMatrixNode, '%s.rotate' % transformNode)

connectPositionCurve()
"""