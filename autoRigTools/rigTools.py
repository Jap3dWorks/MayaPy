# tools for use the rig

from maya import cmds
from maya import OpenMaya
import re
import pymel.core as pm

import logging
logging.basicConfig()
logger = logging.getLogger('rigTools:')
logger.setLevel(logging.DEBUG)


def twistBonesCreator(sections):
    """
    select joints, create twist bones from selected joints to its children
    Args:
        number(int): number twist bones

    Returns(list): twist joints
    """
    selection = pm.ls(sl=True)
    for sel in selection:
        totalNewJoints = []

        if not isinstance(sel, pm.nodetypes.Joint):
            continue
        child = sel.childAtIndex(0)

        value = child.translateX.get() / sections

        twistJoints = [sel]
        for i in range(sections):

            nameList = str(sel).split('_')
            nameList.insert(2, 'twist%s' %(i+1))
            nameTwist=nameList.pop(0)
            for name in nameList:
                nameTwist += '_%s' %name

            twistJoint = sel.duplicate(po=True, name=nameTwist)[0]
            twistJoints[-1].addChild(twistJoint)
            twistJoint.translateX.set(value)
            twistJoints.append(twistJoint)

            if i == sections - 1:
                # last joint bigger
                twistJoint.radius.set(3)

        twistJoints[-1].addChild(child)
        totalNewJoints += twistJoints[1:]

    return totalNewJoints

def snapIkFk(name, zoneA, zoneB, zoneC, side):
    """
    snap ik fk or fk ik
    args:
        name(str): character name
        zoneA(str): zone to snap p.e leg, arm
        zoneB(str): zone below zoneA to snap p.e foot, hand
        zoneC(str): zone below zoneB to snap p.e toe, finger
        side(str): left or right
    """
    attrShape = '%s_%s_%s_attrShape' % (name, zoneA, side)
    attrValue = cmds.getAttr('%s.ikFk' % attrShape)

    # find fk ik Controllers and main
    fkControllers = [i for i in cmds.ls() if
                     re.match('^%s_fk_(%s|%s)_*%s_((?!end).).*ctr$' % (name, zoneA, zoneB, side), str(i))]
    ikControllers = [i for i in cmds.ls() if
                     re.match('^%s_ik_(%s|%s)_*%s_((?!end).).*ctr$' % (name, zoneA, zoneB, side), str(i))]
    mainJoints = [i for i in cmds.ls() if
                  re.match('^%s_main_(%s|%s)_*%s_((?!end).).*joint$' % (name, zoneA, zoneB, side), str(i))]

    ikMatchControllers = []  # controls that are common
    fkMatchControllers = []  # controls that are common
    mainMatchControllers = []  # controls that are common
    poleVectorCtr = None  # pole vector ctr
    ikToeGeneral = None  # general toes control ik
    fkToeGeneral = None  # general toes control fk
    ikFootCtr = None  # ik goot control
    mainFootJoint = None  # main foot joint
    fkFootCtr = None  # fk foot control
    ikBallCtr = None
    # arrange lists to be synchronized
    for ikCtr in list(ikControllers):
        try:
            mainIndex = mainJoints.index(ikCtr.replace('ik', 'main').replace('ctr', 'joint'))
            fkIndex = fkControllers.index(ikCtr.replace('ik', 'fk'))

            if ikCtr == '%s_ik_%s_%s_%s_ctr' % (name, zoneB, side, zoneB):
                ikFootCtr = ikCtr
                ikControllers.remove(ikCtr)
                mainFootJoint = mainJoints.pop(mainIndex)
                fkFootCtr = fkControllers.pop(fkIndex)

            else:
                mainMatchControllers.append(mainJoints.pop(mainIndex))
                fkMatchControllers.append(fkControllers.pop(fkIndex))
                ikMatchControllers.append(ikCtr)
                ikControllers.remove(ikCtr)

        except:
            if 'pole' in ikCtr:
                poleVectorCtr = ikCtr
                ikControllers.remove(ikCtr)

            if 'ball' in ikCtr.lower():
                ikBallCtr = ikCtr

            elif zoneC and '%sGeneral' % zoneC in ikCtr:
                ikToeGeneral = ikCtr
                ikControllers.remove(ikCtr)

                elemetnIndex = fkControllers.index(ikCtr.replace('ik', 'fk'))
                fkToeGeneral = fkControllers.pop(elemetnIndex)

    # ik -> fk
    if attrValue:
        # copy rotation from main joints, this can give som errors in toes, because main joints does not has general toe ctr
        # so we exclude foot and toes
        for i, mainj in enumerate(mainJoints):
            cmds.xform(fkControllers[i], a=True, eu=True, ro=cmds.xform(mainj, a=True, eu=True, q=True, ro=True))

        ikFkCtr = ikBallCtr if ikBallCtr else ikFootCtr  # if we have ikBall use it for the snap
        cmds.xform(fkFootCtr, a=True, ws=True, ro=cmds.xform(ikFkCtr, a=True, ws=True, q=True, ro=True))
        cmds.xform(fkToeGeneral, a=True, ro=cmds.xform(ikToeGeneral, q=True, a=True, ro=True))
        # controllers that match between ik, fk and main.
        for i, fkCtr in enumerate(fkMatchControllers):
            cmds.xform(fkCtr, ws=True, m=cmds.xform(ikMatchControllers[i], ws=True, q=True, m=True))

        cmds.setAttr('%s.ikFk' % attrShape, not attrValue)

    # fk -> ik
    elif not attrValue:
        # reset walk values
        if ikControllers:  # in ikControllers only just left walk controllers
            for attr in ('heel', 'tilt', 'toes', 'ball', 'footRoll'):
                cmds.setAttr('%s.%s' % (ikFootCtr, attr), 0)
                if attr == 'tilt':  # we have two tilts
                    for inOut in ('In', 'Out'):
                        ctrIndex = ikControllers.index(
                            '%s_ik_foot_%s_foot%s%s_ctr' % (name, side, attr.capitalize(), inOut))
                        cmds.xform(ikControllers[ctrIndex], a=True, t=(0, 0, 0), ro=(0, 0, 0), s=(1, 1, 1))
                elif attr == 'footRoll':
                    continue
                else:
                    ctrIndex = ikControllers.index('%s_ik_%s_%s_foot%s_ctr' % (name, zoneB, side, attr.capitalize()))
                    cmds.xform(ikControllers[ctrIndex], a=True, t=(0, 0, 0), ro=(0, 0, 0), s=(1, 1, 1))

        cmds.xform(ikFootCtr, ws=True, m=cmds.xform(fkFootCtr, q=True, ws=True, m=True))
        cmds.xform(ikToeGeneral, a=True, ro=cmds.xform(fkToeGeneral, q=True, a=True, ro=True))
        # snap toes
        for i, ikCtr in enumerate(ikMatchControllers):
            cmds.xform(ikCtr, ws=True, m=cmds.xform(fkMatchControllers[i], ws=True, q=True, m=True))

        if poleVectorCtr:
            # poleVector, use vector additive propriety
            upperLegPos = cmds.xform(mainJoints[0], q=True, ws=True, t=True)
            lowerLegPos = cmds.xform(mainJoints[1], q=True, ws=True, t=True)
            footPos = cmds.xform(mainFootJoint, q=True, ws=True, t=True)

            vector1 = OpenMaya.MVector(lowerLegPos[0] - upperLegPos[0], lowerLegPos[1] - upperLegPos[1],
                                       lowerLegPos[2] - upperLegPos[2])
            vector1.normalize()
            vector2 = OpenMaya.MVector(lowerLegPos[0] - footPos[0], lowerLegPos[1] - footPos[1],
                                       lowerLegPos[2] - footPos[2])
            vector2.normalize()

            poleVectorPos = vector1 + vector2
            poleVectorPos.normalize()
            # multiply the resultant vector by the value we want, this way we can control the distance
            poleVectorPos = poleVectorPos * 20

            # set pole vector position
            cmds.xform(poleVectorCtr, ws=True, t=(
            poleVectorPos.x + lowerLegPos[0], poleVectorPos.y + lowerLegPos[1], poleVectorPos.z + lowerLegPos[2]))

        cmds.setAttr('%s.ikFk' % attrShape, not attrValue)


"""
if __name__ == '__main__':
    snapIkFk('akona', 'leg', 'foot', 'toe', 'left')


import pymel.core as pm
# create 2 cubes, pcube1 and pCube2 with diferent orientations but the same shape position
cube01 = pm.PyNode('pCube1')
cube02 = pm.PyNode('pCube2')

Offset = cube01.getRotation(space='world', quaternion=True)*cube02.getRotation(space='world', quaternion=True).invertIt()
print Offset

Offset.invertIt()

# now rotate cube 1 and apply the line below
cube02.setRotation(Offset*cube01.getRotation(space='world', quaternion=True), 'world')
"""

def neckHeadIsolateSnap(name, zone, controller, point, orient):
    """
    isolate to 0 or 1 and snap controllers
    args:
        name(str): character name
        zone(str): zone of controller
        controller(str): controller type
        point (bool): if true, snap translation
        orient (bool): if true, snap rotation
    """
    headControl = '%s_IK_%s_%s_1_ctr' % (name, zone, controller)

    # check if exist
    if not cmds.objExists(headControl):
        print ('%s do not exists' % headControl)
        return

    # save transforms
    headControlTranslate = cmds.xform(headControl, q=True, ws=True, m=True)

    if orient:
        # set orient
        print ('set orient')
        isolate = not cmds.getAttr('%s.isolateOrient' % headControl)
        cmds.setAttr('%s.isolateOrient' % headControl, isolate)

    if point:
        # set position
        print ('set point')
        isolate = not cmds.getAttr('%s.isolatePoint' % headControl)
        cmds.setAttr('%s.isolatePoint' % headControl, isolate)

    # Transform head control
    cmds.xform(headControl, ws=True, m=headControlTranslate)

"""
if __name__ == '__main__':
    jordiAmposta_Leccion4_tarea2_bonus('akona', 'neckHead', 'head', True, True)
"""

def rootAutoGrps():
    """
    select any number of transform node.
    create a root and a auto group and parent selected object
    """
    selection = cmds.ls(sl=True)
    if not selection:
        print ('Select at least one object')
        return

    for sel in selection:
        # get matrix transformation
        transform = cmds.xform(sel, q=True, ws=True, m=True)

        # query parent
        parent = cmds.listRelatives(p=True)

        # create empty grps
        rootgrp = cmds.group(empty=True, name='%s_root' % sel)
        autoGro = cmds.group(empty=True, name='%s_auto' % sel)

        # set transforms
        cmds.xform(rootgrp, ws=True, m=transform)
        cmds.xform(autoGro, ws=True, m=transform)

        # construct hierarchy
        cmds.parent(sel, autoGro)
        cmds.parent(autoGro, rootgrp)
        # if not has parent, let it under world
        if parent:
            cmds.parent(rootgrp, parent)



