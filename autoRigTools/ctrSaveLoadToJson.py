import pymel.core as pm
import json
import os
from maya.api import OpenMaya

import logging
logging.basicConfig()
logger = logging.getLogger('CtrSaveLoadToJson:')
logger.setLevel(logging.INFO)

# TODO: class type dict. better control and editing
# A method to save the actual state of dict

def ctrSaveJson(typeController, name, path):
    """
    save controllers to json
    Args:
        typeController: controller name
        name: file name
        path: path to save file
    Returns: fullPathName of createdController
    name: [[[[cv],[knots], degree, form],[[cv],[knots], degree, form]],[matrixTransform]]
    """
    # create file path
    controllerFile = ('%s/%s_controllers.json' % (path, name))

    # get selection only use the first element
    selection = pm.ls(sl=True)[0]
    if not selection:
        raise ValueError('Select one nurbs curve')
    
    # if file not exist, create
    if not os.path.exists(controllerFile):
        with open(controllerFile, 'w') as f:
            controllerDict = {}
            json.dump(controllerDict, f, indent=4)
    
    with open(controllerFile, 'r') as f:
        # json to dictionary
        controllerDict = json.load(f)

    # check if we have a previous controller os the same type
    if typeController in controllerDict.keys():
        confirmDialog = pm.confirmDialog(m=('%s is already stored, do you want to replace?' % typeController).capitalize(), button=['Replace','Cancel'])

        if confirmDialog != 'Replace':
            logger.info(('%s %s controller not saved' % (name, typeController)).capitalize())
            return

    # here save list attributes
    controllerAttr = []

    curveShapes = selection.listRelatives(s=True, c=True, type='nurbsCurve')
    for curveShape in curveShapes:
        print curveShape
        if not isinstance(curveShape, pm.nodetypes.NurbsCurve):
            raise ValueError('Controller must be a nurbs curve')
        shapeAttr = []
        points = curveShape.getCVs()
        # points must be list of floats
        shapeAttr.append([(i.x, i.y, i.z) for i in points])
        shapeAttr.append(curveShape.getKnots())
        shapeAttr.append(curveShape.attr('degree').get())
        shapeAttr.append(curveShape.attr('form').get())

        # one list per shape in the controller
        controllerAttr.append(shapeAttr)
        # todo: append matrix transform

    matrixTransform = pm.xform(selection, q=True, ws=True, m=True)
    # save controller to dictionary
    controllerDict[typeController] = controllerAttr, matrixTransform

    # save to json
    with open(controllerFile, 'w') as f:
        json.dump(controllerDict, f, indent=4)

    logger.info('%s %s controller saved at: %s' % (name, typeController, controllerFile))


def ctrLoadJson(typeController, name, path, SFactor=1, ColorIndex = 4):
    """
    Load saved controllers from json
    Args:
        typeController: controller name
        name: file name
        path: path of file
        SFactor: scale factor
        ColorIndex: color index
    Returns: fullPathName of createdController, transform matrix
    """
    controllerFile = ('%s/%s_controllers.json' % (path, name))

    # load json
    with open(controllerFile, 'r') as f:
        # json to dictionary
        controllerDict = json.load(f)

    # list with controller parameters
    ctrParameters = controllerDict[typeController][0]
    transform = OpenMaya.MObject()
    for n, ctrParam in enumerate(ctrParameters):
        curveFn = OpenMaya.MFnNurbsCurve()
        # create controller
        form = curveFn.kOpen if ctrParam[3] == 0 else curveFn.kPeriodic
        # multiplyFactor
        CVPoints = [(i[0]*SFactor, i[1]*SFactor, i[2]*SFactor) for i in ctrParam[0]]
        # create curve
        curveFn.create(CVPoints, ctrParam[1], ctrParam[2], form, False, True,
                       transform if isinstance(transform, OpenMaya.MObject) else transform.node())
        # set color
        enhableColorsPlug = curveFn.findPlug('overrideEnabled', False)
        enhableColorsPlug.setBool(True)
        colorPlug = curveFn.findPlug('overrideColor', False)
        colorPlug.setInt(ColorIndex)
        newControllerDagPath = OpenMaya.MDagPath.getAPathTo(curveFn.object())
        if n == 0:
            transform = OpenMaya.MDagPath.getAPathTo(newControllerDagPath.transform())

    # return controller name, and saved matrix transform
    return transform.fullPathName(), controllerDict[typeController][1]


def mirrorControllers():
    """
    mirror the selected controllers.
    like mirror joints, behaviour
    Returns: list with mirrored controllers
    """
    selection = pm.ls(sl=True)

    mirroredControllers =[]
    for sel in selection:
        # sides the script will detect
        sides = ['left', 'right']
        side = None

        for i, s in enumerate(sides):
            if s in str(sel):
                oldSide = s
                side = sides[(i + 1) % 2]

        if not side:
            # if side is not defined, don't mirror
            continue

        pm.xform(sel, ztp=True)
        # duplicate controller
        newController = sel.duplicate(name=str(sel).replace(oldSide, side))[0]
        group = pm.group(empty=True)

        # symmetrize to -X or +X
        group.addChild(newController)
        group.scaleX.set(-1)

        newController.setParent(world=True)
        matrix = pm.xform(q=True, ws=True, m=True)
        # orient the transform matrix vectors to correct side
        pm.xform(group, ws=True,
                 m=(-matrix[0], -matrix[1], -matrix[2], matrix[3], -matrix[4], -matrix[5], -matrix[6], matrix[7],
                    -matrix[8], -matrix[9], -matrix[10], matrix[11], matrix[12], matrix[13], matrix[14], matrix[15]))

        group.addChild(newController)
        # freeze the controller transforms under a group with the desired orientation
        pm.makeIdentity(newController, a=True, t=True, r=True, s=True, pn=1)
        newController.setParent(world=True)
        # delete unnecessary objects
        pm.delete(group)
        # save new controller
        mirroredControllers.append(newController)

    return mirroredControllers

"""
import maya.cmds as cmds

def saveControllersSelection():
    selection = cmds.ls(sl=True)
    cmds.select(cl=True)
    for sel in selection:
        cmds.select(sel, r=True)
        try:
            autoRigTools.ctrSaveLoadToJson.ctrSaveJson(sel,'akona', 'D:\_docs\_Animum\Akona')
        except:
            pass
        cmds.select(cl=True)

saveControllersSelection()
"""