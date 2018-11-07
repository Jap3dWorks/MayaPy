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
    """
    # create file path
    controllerFile = ('%s/%s.json' % (path, name))

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

    # list where save list attributes
    controllerAttr = []

    curveShapes = selection.listRelatives(s=True, c=True)
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
    
    # save controller to dictionary
    controllerDict[typeController] = controllerAttr

    # save to json
    with open(controllerFile, 'w') as f:
        json.dump(controllerDict, f, indent=4)

    logger.info('%s %s controller saved at: %s' % (name, typeController, controllerFile))


def ctrLoadJson(typeController, name, path, SFactor=1, ColorIndex = 4):
    """
    TODO: color attributes here too
    Load saved controllers from json
    Args:
        typeController: controller name
        name: file name
        path: path of file
        SFactor: scale factor
    Returns: fullPathName of createdController
    """
    controllerFile = ('%s/%s.json' % (path, name))

    # load json
    with open(controllerFile, 'r') as f:
        # json to dictionary
        controllerDict = json.load(f)

    # list with controller parameters
    ctrParameters = controllerDict[typeController]
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

    return transform.fullPathName()