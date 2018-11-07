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
    
    # if file not exist, create
    if not os.path.exists(controllerFile):
        with open(controllerFile, 'w') as f:
            controllerDict = {}
            json.dump(controllerDict, f, indent=4)
    
    with open(controllerFile, 'r') as f:
        # json to dictionary
        controllerDict = json.load(f)
    
    # list where save list attributes
    controllerAttr = []
    # points must be list of floats
    curveShape = selection.getShape()
    points = curveShape.getCVs()
    controllerAttr.append([(i.x, i.y, i.z) for i in points])
    controllerAttr.append(curveShape.getKnots())
    controllerAttr.append(curveShape.attr('degree').get())
    controllerAttr.append(curveShape.attr('form').get())
    
    # save controller to dictionary
    controllerDict[typeController] = controllerAttr
    
    # save to json
    with open(controllerFile, 'w') as f:
        json.dump(controllerDict, f, indent=4)

def ctrLoadJson(typeController, name, path, SFactor=1):
    """
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
    curveFn = OpenMaya.MFnNurbsCurve()
    # create controller
    form = curveFn.kOpen if ctrParameters[3] == 0 else curveFn.kPeriodic
    # multiplyFactor
    CVPoints = [(i[0]*SFactor, i[1]*SFactor, i[2]*SFactor) for i in ctrParameters[0]]
    # create curve
    curveFn.create(CVPoints, ctrParameters[1], ctrParameters[2], form, False, True)
    newControllerDagPath = OpenMaya.MDagPath.getAPathTo(curveFn.object())
    
    return OpenMaya.MDagPath.getAPathTo(newControllerDagPath.transform()).fullPathName()