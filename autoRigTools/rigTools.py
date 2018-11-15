# tools for use the rig
from maya import cmds
from maya import OpenMaya
import re
import pymel.core as pm

import logging
logging.basicConfig()
logger = logging.getLogger('rigTools:')
logger.setLevel(logging.DEBUG)

def snapIkFkLeg(name, zone, side):
    """
    change to ik and fk and snap controllers
    args:
        name(str): character name
        zone(str): zone of controller
        side(str): left or right
        direction(bool): 1: ik to fk. 2: fk to ik
    """
    quaternionOffset = pm.datatypes.Quaternion(0.511546727083, -0.488180239267, -0.511546727083, 0.488180239267)
    logger.debug('quaternionOffset : %s, %s, %s, %s ' % (quaternionOffset.x, quaternionOffset.y, quaternionOffset.z, quaternionOffset.w))
    ikFkNode = pm.PyNode('%s_%s_%s_attr' % (name, zone, side))
    # find fk Controllers
    # review: it's is a little stupid ask for the zone and then put upperleg manually
    fkControllers = [i for i in pm.ls() if re.match('^%s_fk_%s_%s_((upperleg)|(lowerleg)|(leg))_ctr$' % (name, zone, side), str(i))]
    logger.debug('fk controls: %s' % fkControllers)

    # find ik joints
    ikJoints = [i for i in pm.ls() if re.match('^%s_ik_joint_%s_%s_((upperleg)|(lowerleg)|(leg))_joint$' % (name, zone, side), str(i))]
    logger.debug('ik joints: %s' % ikJoints)
    # find ik control
    ikControl = pm.PyNode('%s_ik_%s_%s_ctr' % (name, zone, side))

    # ik to fk
    if not ikFkNode.ikFk.get():
        # poleVector
        poleVector = pm.PyNode('%s_ik_%s_%s_pole_ctr' % (name, zone, side))

        # rotation offset
        mquaternion = fkControllers[-1].getRotation(space='world', quaternion=True)
        logger.debug('mquaternion : %s, %s, %s, %s ' % (mquaternion.x, mquaternion.y, mquaternion.z, mquaternion.w))
        #mquaternion.invertIt()
        #logger.debug('mquaternion : %s, %s, %s, %s ' % (mquaternion.x, mquaternion.y, mquaternion.z, mquaternion.w))

        fkFootRot = fkControllers[-1].getRotation('world')
        ikFootRot = ikControl.getRotation('world')

        # ikRotOffset = fkFootRot - ikFootRot
        # logger.debug('ik control foot offset: %s, %s, %s' % (ikRotOffset.x, ikRotOffset.y, ikRotOffset.z))

        # ikRotOffset = OpenMaya.MEulerRotation(1.57079632679, 0.0467372293198, -1.57079632679)


        # setTransforms
        quaternionOffset.invertIt()
        # pm.xform(ikControl, ws=True, m=pm.xform(fkControllers[-1], q=True, ws=True, m=True))
        ikControl.setTranslation(fkControllers[-1].getTranslation('world'), 'world')

        quat01 = quaternionOffset*fkControllers[-1].getRotation(space='world', quaternion=True)
        logger.debug('quat01 : %s, %s, %s, %s ' % (quat01.x, quat01.y, quat01.z, quat01.w))
        quat02 = fkControllers[-1].getRotation(space='world', quaternion=True) * quaternionOffset
        logger.debug('quat02 : %s, %s, %s, %s ' % (quat02.x, quat02.y, quat02.z, quat02.w))

        quat01.invertIt()
        logger.debug('quat01 invert : %s, %s, %s, %s ' % (quat01.x, quat01.y, quat01.z, quat01.w))
        quat02.invertIt()
        logger.debug('quat02 : %s, %s, %s, %s ' % (quat02.x, quat02.y, quat02.z, quat02.w))



        ikControl.setRotation(quaternionOffset*fkControllers[-1].getRotation(space='world', quaternion=True), 'world')



        # ikControl.setRotation(quaternionOffset, 'world')

        #ikControl.setScale(fkControllers[-1].getScale())

        # set ikfk attr
        ikFkNode.ikFk.set(1)

        # set poleVector
        kneePoss = fkControllers[1].getTranslation('world')
        vector1 = kneePoss - fkControllers[0].getTranslation('world')
        vector1.normalize()
        vector2 = kneePoss - fkControllers[-1].getTranslation('world')
        vector2.normalize()

        # poleVector vector
        pvVector = vector2 + vector1
        pvVector.normalize()

        # set polevector position
        poleVector.setTranslation(pvVector * 25 + kneePoss, 'world')

    # fk to ik
    if ikFkNode.ikFk.get():
        pass




def snapIsolateHead(name, zone, controller, point, orient, isolate):
    """
    set isolate to 0 or 1 and snap controllers
    args:
        name(str): character name
        zone(str): zone of controller
        controller(str): controller type
        point (bool): if true, snap translation
        orient (bool): if true, snap rotation
        isolate(bool): if true change to isolate mode, if false change to normal mode
    """
    headControl = '%s_IK_%s_%s_1_ctr' % (name, zone, controller)

    headControlTranslate = cmds.xform(headControl, q=True, ws=True, t=True)
    print('translate:%s' % headControlTranslate)
    headControlRotate = cmds.xform(headControl, q=True, ws=True, ro=True)
    print('orient:%s' % headControlRotate)

    if orient:
        print 'set orient'
        cmds.setAttr('%s.isolateOrient' % headControl, isolate)
        cmds.xform(headControl, ws=True, ro=headControlRotate)

    if point:
        print 'set point'
        cmds.setAttr('%s.isolatePoint' % headControl, isolate)
        cmds.xform(headControl, ws=True, t=headControlTranslate)

