# tools for use the rig

from maya import cmds
from maya import OpenMaya
import re
import pymel.core as pm

import logging
logging.basicConfig()
logger = logging.getLogger('rigTools:')
logger.setLevel(logging.DEBUG)


def snapIkFk(name, side):
    """
    snap ik fk or fk ik
    args:
        name(str): character name
        side(str): left or right
    """
    attrShape = '%s_leg_%s_attrShape' % (name, side)
    attrValue = cmds.getAttr('%s.ikFk' % attrShape)

    # find fk ik Controllers and main
    fkControllers = [i for i in cmds.ls() if re.match('^%s_fk_(leg|foot)_*%s_((?!end).).*ctr$' % (name, side), str(i))]
    ikControllers = [i for i in cmds.ls() if re.match('^%s_ik_(leg|foot)_*%s_((?!end).).*ctr$' % (name, side), str(i))]
    mainJoints = [i for i in cmds.ls() if re.match('^%s_main_(leg|foot)_*%s_((?!end).).*joint$' % (name, side), str(i))]

    # arrange lists to be sincronized
    ikMatchControllers = []
    fkMatchControllers = []
    for fkCtr in list(fkControllers):
        try:
            elemetnIndex = ikControllers.index(fkCtr.replace('fk', 'ik'))
            ikMatchControllers.append(ikControllers.pop(elemetnIndex))
            fkMatchControllers.append(fkCtr)
        except:
            pass

    # ik -> fk
    if attrValue:
        # copy ro from main joints, this can give som errors in toes, because main does not has general toe ctr
        # so we exclude foot and toes
        for i, mainj in enumerate(mainJoints[:2]):
            cmds.xform(fkControllers[i], a=True, eu=True, ro=cmds.xform(mainj, a=True, eu=True, q=True, ro=True))

        # controllers that match between ik and fk, this fix erros with toes tODO: test snap with main. error with footwalk toes
        for i, fkCtr in enumerate(fkMatchControllers):
            if i == 0:
                # first ctr, foot ctr in world space
                cmds.xform(fkCtr, a=True, ws=True, ro=cmds.xform('%s_fkSync' % fkCtr, a=True, ws=True, q=True, ro=True))
            else:
                cmds.xform(fkCtr, a=True, eu=True,
                           ro=cmds.xform(ikMatchControllers[i], a=True, eu=True, q=True, ro=True))

        cmds.setAttr('%s.ikFk' % attrShape, not attrValue)

    # fk -> ik
    elif not attrValue:
        # reset walk values
        for attr in ('Heel', 'Tilt', 'Toes', 'Ball', 'FootRoll'):
            cmds.setAttr('%s.%s' % (ikMatchControllers[0], attr[0].lower() + attr[1:]), 0)

            if attr == 'Tilt':  # we have two tilts
                for inOut in ('In', 'Out'):
                    ctrIndex = ikControllers.index('%s_ik_foot_%s_foot%s%s_ctr' % (name, side, attr, inOut))
                    cmds.xform(ikControllers[ctrIndex], a=True, t=(0, 0, 0), ro=(0, 0, 0), s=(1, 1, 1))
            elif attr == 'FootRoll':
                continue
            else:
                ctrIndex = ikControllers.index('%s_ik_foot_%s_foot%s_ctr' % (name, side, attr))
                cmds.xform(ikControllers[ctrIndex], a=True, t=(0, 0, 0), ro=(0, 0, 0), s=(1, 1, 1))

        # snap foot and toes
        for i, ikCtr in enumerate(ikMatchControllers):
            if i == 0:
                # first ctr, foot ctr in world space
                cmds.xform(ikCtr, ws=True, m=cmds.xform(fkMatchControllers[i], ws=True, q=True, m=True))
            else:
                cmds.xform(ikCtr, a=True, eu=True,
                           ro=cmds.xform(fkMatchControllers[i], a=True, eu=True, q=True, ro=True))

        # poleVector, use vector additive propiety
        upperLegPos = cmds.xform(mainJoints[0], q=True, ws=True, t=True)
        lowerLegPos = cmds.xform(mainJoints[1], q=True, ws=True, t=True)
        footPos = cmds.xform(mainJoints[2], q=True, ws=True, t=True)

        vector1 = OpenMaya.MVector(lowerLegPos[0] - upperLegPos[0], lowerLegPos[1] - upperLegPos[1],
                                   lowerLegPos[2] - upperLegPos[2])
        vector1.normalize()
        vector2 = OpenMaya.MVector(lowerLegPos[0] - footPos[0], lowerLegPos[1] - footPos[1],
                                   lowerLegPos[2] - footPos[2])
        vector2.normalize()

        poleVectorPos = vector1 + vector2
        poleVectorPos.normalize()
        poleVectorPos = poleVectorPos * 20

        # pole vector is the first index of the ikcontrollers. TODO. index for pole vector
        cmds.xform(ikControllers[0], ws=True, t=(
        poleVectorPos.x + lowerLegPos[0], poleVectorPos.y + lowerLegPos[1], poleVectorPos.z + lowerLegPos[2]))

        cmds.setAttr('%s.ikFk' % attrShape, not attrValue)


if __name__ == '__main__':
    snapIkFk('akona', 'left')

"""
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


def jordiAmposta_Leccion4_tarea2_bonus(name, zone, controller, point, orient):
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


if __name__ == '__main__':
    jordiAmposta_Leccion4_tarea2_bonus('akona', 'neckHead', 'head', True, True)

