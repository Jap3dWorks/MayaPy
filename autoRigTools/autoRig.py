import pymel.core as pm
import re
from maya import OpenMaya

import logging
logging.basicConfig()
logger = logging.getLogger('autoSpine:')
logger.setLevel(logging.DEBUG)

class autoRig(object):
    def __init__(self, chName='akona'):
        """
        autoRig class tools
        """
        # TODO: node 'unknown' messages attributes to store connections?
        self.chName = chName
        self.joints = {}  # store joints
        self.ikControllers = {}

        # create necessary groups
        # check if noXform exist
        try:
            self.noXformGrp = pm.PyNode('%s_noXform_grp' % self.chName)
        except:
            self.noXformGrp = pm.group(name='%s_noXform_grp' % self.chName, empty=True)
            self.noXformGrp.inheritsTransform.set(False)
            pm.PyNode('%s_rig_grp' % self.chName).addChild(self.noXformGrp)

        # check if ctr_grp exist
        try:
            self.ctrGrp = pm.PyNode('%s_ctr_grp' % self.chName)
        except:
            self.ctrGrp = pm.group(name='%s_ctr_grp' % self.chName, empty=True)
            pm.PyNode('%s_rig_grp' % self.chName).addChild(self.ctrGrp)


    def autoSpine(self, zone='spine'):
        """
            Auto create a character spine
        """

        # detect spine joints and their positions
        spineJoints = [i for i in pm.ls() if re.match('^%s.*((hips)|(spine)|(chest)).*joint$' % self.chName, str(i))]
        positions = [i.getTranslation(space='world') for i in spineJoints]

        spineCurveTransform = pm.curve(ep=positions, name='%s_spine_1_crv' % self.chName)
        # parent to nXform grp
        noXformSpineGrp = pm.group(empty=True, name='%s_noXform_spine_grp' % self.chName)
        noXformSpineGrp.inheritsTransform.set(False)
        self.noXformGrp.addChild(noXformSpineGrp)
        noXformSpineGrp.addChild(spineCurveTransform)

        # curve shape node
        spineCurve = spineCurveTransform.getShape()

        #rebuildCurve
        pm.rebuildCurve(spineCurve, s=2, rpo=True, ch=False, rt=0, d=3, kt=0, kr=0)

        # review: manual adjust
        # TODO: search an automation, use  distanceToCurve
        spineCurve.setCV(1, spineCurve.getCV(1)+(0, 0, 0.574351))
        spineCurve.setCV(3, spineCurve.getCV(3)+(0, 0, -0.646978))

        # create locators and connect to curve CV's
        spineDrvList = []
        spineIKControllerList = []
        spineFKControllerList = []
        for n, i in enumerate(spineCurve.getCVs()):
            # TODO: nice ik controllers shape
            # create grp to manipulate the curve
            spineDriver = pm.group(name='%s_spineCurve_%s_drv' % (self.chName, n+1), empty=True)
            spineDriver.setTranslation(i)
            decomposeMatrix = pm.createNode('decomposeMatrix', name='%s_spine_%s_decomposeMatrix' % (self.chName, n+1))
            spineDriver.worldMatrix[0].connect(decomposeMatrix.inputMatrix)
            decomposeMatrix.outputTranslate.connect(spineCurve.controlPoints[n])
            spineDrvList.append(spineDriver)

            # create controller and parent locator
            spineController = createController('%s_spine_IK_%s_ctr' % (self.chName, n+1), 'circle')
            logger.debug('spine controller: %s' % spineController)
            spineController.setTranslation(i)
            spineController.addChild(spineDriver)
            spineIKControllerList.append(spineController)

            # create FK controllers
            if n < 3:
                # first fk controller bigger
                fkCtrSize = 1.5 if len(spineFKControllerList) == 0 else 1
                spineFKController = createController('%s_spine_FK_%s_ctr' % (self.chName, n + 1), 'square', fkCtrSize)
                spineFKController.setTranslation(i)
                spineFKControllerList.append(spineFKController)

                # Fk hierarchy
                if len(spineFKControllerList) > 1:
                    spineFKControllerList[n-1].addChild(spineFKController)
                    logger.debug('parent %s, child %s' % (spineFKControllerList[-1], spineFKController))

            # configure ctr hierarchy, valid for 5 ctrllers
            if n == 1:
                spineIKControllerList[0].addChild(spineController)
                spineFKControllerList[0].addChild(spineIKControllerList[0])
            # last iteration
            elif n == (spineCurve.numCVs()-1):
                spineController.addChild(spineIKControllerList[-2])
                spineFKControllerList[-1].addChild(spineController)

                # add 3th ik controller to hierarchy too
                spineFKControllerList[1].addChild(spineIKControllerList[2])
                self.ctrGrp.addChild(spineFKControllerList[0])

        # create roots grp
        createRoots(*spineFKControllerList)
        createRoots(*spineIKControllerList)

        # once created roots, we can freeze and hide attributes. if not, it can be unstable
        for neckHeadIKCtr in spineFKControllerList[1:]:
            neckHeadIKCtr.translate.lock()
            for axis in ('X','Y','Z'):
                pm.setAttr('%s.translate%s' % (str(neckHeadIKCtr), axis), channelBox=False, keyable=False)

        # create points on curve that will drive the joints
        jointDriverList = []
        ObjectUpVectorList = []
        for n, joint in enumerate(spineJoints):
            # jointPosition
            jointPos = joint.getTranslation('world')

            # nurbsCurve MFn
            selectionList = OpenMaya.MSelectionList()
            selectionList.add(str(spineCurve))
            dagPath = OpenMaya.MDagPath()
            selectionList.getDagPath(0, dagPath)
            mfnNurbCurve = OpenMaya.MFnNurbsCurve(dagPath)

            # get curveParam
            util = OpenMaya.MScriptUtil()
            util.createFromDouble(0.0)
            ptr = util.asDoublePtr()
            mfnNurbCurve.getParamAtPoint(OpenMaya.MPoint(jointPos[0], jointPos[1], jointPos[2]), ptr, 1.0)
            param = util.getDouble(ptr)

            # create empty grp and connect nodes
            # TODO: no locator, empty grp
            jointDriverGrp = pm.group(empty=True, name='%s_target' % str(joint))
            # jointDriverGrp = pm.spaceLocator(name='%s_target' % str(joint))
            pointOnCurveInfo = pm.createNode('pointOnCurveInfo', name='%s_spine_joint_%s_positionOnCurveInfo' % (self.chName, n+1))
            spineCurve.worldSpace[0].connect(pointOnCurveInfo.inputCurve)
            pointOnCurveInfo.parameter.set(param)
            pointOnCurveInfo.position.connect(jointDriverGrp.translate)
            noXformSpineGrp.addChild(jointDriverGrp)
            # drive joint by a parent constraint
            jointDriverList.append(jointDriverGrp)

            # up vector transforms, useful for later aimContraint
            ObjectUpVector = pm.group(empty=True, name='%s_upVector' % str(joint))
            # ObjectUpVector = pm.spaceLocator(name='%s_upVector' % str(joint))
            ObjectUpVector.setTranslation(jointDriverGrp.getTranslation() + pm.datatypes.Vector(0, 0, -20), 'world')
            noXformSpineGrp.addChild(ObjectUpVector)
            ObjectUpVectorList.append(ObjectUpVector)

            # AimConstraint locators, each locator aim to the upper locator
            if n == 0:
                # parent first target transform, to hips controller
                spineIKControllerList[0].addChild(ObjectUpVector)
            else:
                aimConstraint = pm.aimConstraint(jointDriverList[-1], jointDriverList[-2], aimVector=(1,0,0), upVector=(0,1,0), worldUpType='object', worldUpObject=ObjectUpVectorList[-2])

        # parent last target transform, to chest
        spineIKControllerList[-1].addChild(ObjectUpVectorList[-1])
        # review: create parent constraints, once drivers have been created, if not, all flip
        for i in range(len(spineJoints[:-1])):
            pm.parentConstraint(jointDriverList[i], spineJoints[i], maintainOffset=True, name='%s_parentConstraint' % str(joint))

        # connect by pointcontraint objectUpVector to first and last upVectors
        totalDistance = ObjectUpVectorList[-1].getTranslation('world') - ObjectUpVectorList[0].getTranslation('world')
        logger.debug('totalDistance: %s' % totalDistance)
        totalDistance = totalDistance.length()
        logger.debug('totalDistance: %s' % totalDistance)

        for n, upVectorObject in enumerate(ObjectUpVectorList):
            if n == 0 or n == len(ObjectUpVectorList)-1:
                continue
            distance = upVectorObject.getTranslation('world') - ObjectUpVectorList[0].getTranslation('world')
            distance = distance.length()
            pointConstraintFactor = distance/totalDistance

            pointContraint = pm.pointConstraint(ObjectUpVectorList[-1], ObjectUpVectorList[0], upVectorObject, maintainOffset=False, name='%s_pointConstraint' % str(upVectorObject))
            pointContraint.attr('%sW0' % str(ObjectUpVectorList[-1])).set(pointConstraintFactor)
            pointContraint.attr('%sW1' % str(ObjectUpVectorList[0])).set(1-pointConstraintFactor)

        # stretch squash spine
        # curveInfo and connect spineCurve
        curveInfo = pm.createNode('curveInfo')
        spineCurve.worldSpace[0].connect(curveInfo.inputCurve)
        spineCurveLength = spineCurve.length()

        # create anim curve to control scale influence
        # maybe this is better to do with a curveAttr
        scaleInfluenceCurve = pm.createNode('animCurveTU')
        scaleInfluenceCurve.addKeyframe(0, 0.0)
        scaleInfluenceCurve.addKeyframe(len(spineJoints)//2, 1.0)
        scaleInfluenceCurve.addKeyframe(len(spineJoints)-1, 0.0)
        for n, joint in enumerate(spineJoints):
            # for each joint, create a multiply divide node
            # formula for scale: 1+(factorScale - 1)*influence
            # TODO: rename all this
            if re.match('.*chest.*', str(joint)):
                continue
            multiplyDivide = pm.createNode('multiplyDivide')
            multiplyDivide.operation.set(2)
            multiplyDivide.input1X.set(spineCurveLength)
            curveInfo.arcLength.connect(multiplyDivide.input2X)
            plusMinusAverage = pm.createNode('plusMinusAverage')
            multiplyDivide.outputX.connect(plusMinusAverage.input1D[0])
            plusMinusAverage.input1D[1].set(-1)
            multiplyDivideInfluence = pm.createNode('multiplyDivide')
            plusMinusAverage.output1D.connect(multiplyDivideInfluence.input1X)
            # frame cache
            frameCache = pm.createNode('frameCache')
            scaleInfluenceCurve.output.connect(frameCache.stream)
            frameCache.varyTime.set(n)
            frameCache.varying.connect(multiplyDivideInfluence.input2X)
            # plus 1
            plusMinusAverageToJoint = pm.createNode('plusMinusAverage')
            multiplyDivideInfluence.outputX.connect(plusMinusAverageToJoint.input1D[0])
            plusMinusAverageToJoint.input1D[1].set(1)

            # connect to joint
            plusMinusAverageToJoint.output1D.connect(joint.scaleY)
            plusMinusAverageToJoint.output1D.connect(joint.scaleZ)

    # save data
        self.joints[zone] = spineJoints
        self.ikControllers[zone] = spineIKControllerList


    def autoNeckHead(self, zone='neckHead'):
        # store joints, not end joint
        neckHeadJoints = [i for i in pm.ls() if re.match('^%s.*(neck|head).*joint$' % self.chName, str(i))]
        logger.debug('Neck head joints: %s' % neckHeadJoints)
        positions = [i.getTranslation(space='world') for i in neckHeadJoints[:-1]]
        positions.append((positions[-1][0],positions[-1][1]+3,positions[-1][2]))

        neckHeadCurveTransform = pm.curve(ep=positions, name='%s_spine_1_crv' % self.chName)
        # parent to noXform grp
        noXformNeckHeadGrp = pm.group(empty=True, name='%s_noXform_neck_head_grp' % self.chName)
        noXformNeckHeadGrp.inheritsTransform.set(False)
        self.noXformGrp.addChild(noXformNeckHeadGrp)
        noXformNeckHeadGrp.addChild(neckHeadCurveTransform)

        neckHeadCurve = neckHeadCurveTransform.getShape()

        # rebuildCurve
        pm.rebuildCurve(neckHeadCurve, s=2, rpo=True, ch=False, rt=0, d=3, kt=0, kr=0)

        # review: manual adjust
        # TODO: search an automation, use  distanceToCurve
        neckHeadCurve.setCV(1, neckHeadCurve.getCV(1) + (0, 0, 0.466137))

        # create locators and connect to curve CV's
        neckHeadDrvList = []
        neckHeadIKCtrList = []
        neckHeadFKCtrList = []

        for n, i in enumerate(neckHeadCurve.getCVs()):
            # TODO: nice ik controllers shape
            # create drivers to manipulate the curve
            neckHeadDriver = pm.group(name='%s_neckHeadCurve_%s_drv' % (self.chName, n+1), empty=True)
            neckHeadDriver.setTranslation(i)
            # use the worldMatrix
            decomposeMatrix = pm.createNode('decomposeMatrix', name='%s_neckHead_%s_decomposeMatrix' % (self.chName, n+1))
            neckHeadDriver.worldMatrix[0].connect(decomposeMatrix.inputMatrix)
            decomposeMatrix.outputTranslate.connect(neckHeadCurve.controlPoints[n])
            # set last ik spine controller as parent
            self.ikControllers['spine'][-1].addChild(neckHeadDriver)
            neckHeadDrvList.append(neckHeadDriver)  # add to drv List

            # no create controller two first drivers and the penultimate
            if n > 1 and not n == neckHeadCurve.numCVs()-1:
                # create controller and parent drivers to controllers
                neckHeadIKCtr = createController('%s_neckHead_IK_%s_ctr' % (self.chName,len(neckHeadIKCtrList)+1),'circle',.5)
                logger.debug('neckHead controller: %s' % neckHeadIKCtr)

                # second controller more smooth deform up the first
                ikCtrPos = i if len(neckHeadIKCtrList) == 0 else (neckHeadIKCtrList[-1].getTranslation('world')[0],i[1],neckHeadIKCtrList[-1].getTranslation('world')[2])
                neckHeadIKCtr.setTranslation(ikCtrPos)
                neckHeadIKCtr.addChild(neckHeadDriver)
                neckHeadIKCtrList.append(neckHeadIKCtr)  # add to ik controller List

                # create FK controllers, only with the first ik controller
                if len(neckHeadIKCtrList) == 1:
                    neckHeadFKCtr = createController('%s_neckHead_FK_%s_ctr' % (self.chName,len(neckHeadFKCtrList)+1),'square',.5)
                    neckHeadFKCtr.setTranslation(i)
                    neckHeadFKCtrList.append(neckHeadFKCtr)
                    # Fk hierarchy, if we have more fk controllers. not the case
                    if len(neckHeadFKCtrList) > 1:
                        neckHeadFKCtrList[n-1].addChild(neckHeadFKCtr)
                        logger.debug('parent %s, child %s' % (neckHeadFKCtrList[-1], neckHeadFKCtr))

        # configure ctr hierarchy
        neckHeadFKCtrList[-1].addChild(neckHeadIKCtrList[-1])
        neckHeadIKCtrList[-1].addChild(neckHeadDrvList[-1])  # add the penultimate driver too
        self.ikControllers['spine'][-1].addChild(neckHeadIKCtrList[0])  # ik controller child of last spine controller
        neckHeadIKCtrList[0].addChild(neckHeadDrvList[1])
        neckHeadIKCtrList[-1].rename('%s_head_IK_1_ctr' % self.chName)
        # Fk parent to last ik spine controller
        self.ikControllers['spine'][-1].addChild(neckHeadFKCtrList[-1])

        # create roots grp
        neckHeadFKCtrRoots = createRoots(*neckHeadFKCtrList)
        neckHeadIKCtrRoots = createRoots(*neckHeadIKCtrList)
        # once created roots, we can freeze and hide attributes. if not, it can be unstable
        for neckHeadIKCtr in neckHeadFKCtrList:
            neckHeadIKCtr.translate.lock()
            for axis in ('X','Y','Z'):
                pm.setAttr('%s.translate%s' % (str(neckHeadIKCtr), axis), channelBox=False, keyable=False)

        # head orient auto
        # head orient neck grp
        neckOrientAuto = pm.group(empty=True, name='%s_head_orientAuto_head_grp' % self.chName)
        neckOrientAuto.setTranslation(neckHeadIKCtrList[-1].getTranslation('world'), 'world')
        neckHeadFKCtrList[-1].addChild(neckOrientAuto)

        headIkAutoGrp = pm.group(empty=True, name='%s_head_ikAuto_grp' % self.chName)
        headIkAutoGrp.setTranslation(neckHeadIKCtrList[-1].getTranslation('world'), 'world')
        neckHeadFKCtrList[-1].addChild(headIkAutoGrp)
        headIkAutoGrp.addChild(neckHeadIKCtrRoots[-1])

        # head orient base grp
        baseOrientAuto = pm.group(empty=True, name='%s_head_orientAuto_base_grp' % self.chName)
        baseOrientAuto.setTranslation(neckOrientAuto.getTranslation('world'), 'world')
        self.ctrGrp.addChild(baseOrientAuto)

        # create driver attr
        pm.addAttr(neckHeadIKCtrList[-1], longName='Isolate', shortName='Isolate', minValue=0.0,
                   maxValue=1.0, type='float', defaultValue=0.0, k=True)

        # constraint head controller offset to orient auto grps
        autoOrientConstraint = pm.parentConstraint(baseOrientAuto, neckOrientAuto, headIkAutoGrp, maintainOffset=False, name='%s_head_autoOrient_parentConstraint' % self.chName)

        # create Nodes and connect
        neckHeadIKCtrList[-1].Isolate.connect(autoOrientConstraint.attr('%sW0' % str(baseOrientAuto)))

        plusMinusAverage = pm.createNode('plusMinusAverage', name='%s_head_orientAuto_isolate_plusMinusAverage' % self.chName)
        neckHeadIKCtrList[-1].Isolate.connect(plusMinusAverage.input1D[1])
        plusMinusAverage.input1D[0].set(1)
        plusMinusAverage.operation.set(2)
        plusMinusAverage.output1D.connect(autoOrientConstraint.attr('%sW1' % str(neckOrientAuto)))

        # create points on curve that will drive the joints
        jointDriverList = []
        ObjectUpVectorList = []
        for n, joint in enumerate(neckHeadJoints):
            # jointPosition
            jointPos = joint.getTranslation('world')

            # nurbsCurve MFn
            selectionList = OpenMaya.MSelectionList()
            selectionList.add(str(neckHeadCurve))
            dagPath = OpenMaya.MDagPath()
            selectionList.getDagPath(0, dagPath)
            mfnNurbCurve = OpenMaya.MFnNurbsCurve(dagPath)

            # get curveParam
            util = OpenMaya.MScriptUtil()
            util.createFromDouble(0.0)
            ptr = util.asDoublePtr()
            try:
                mfnNurbCurve.getParamAtPoint(OpenMaya.MPoint(jointPos[0], jointPos[1], jointPos[2]), ptr, 1.0)
                param = util.getDouble(ptr)
            except:
                param = 1.0
            # create empty grp and connect nodes
            # TODO: no locator, empty grp
            #jointDriverGrp = pm.group(empty=True, name='%s_target' % str(joint))
            jointDriverGrp = pm.spaceLocator(name='%s_target' % str(joint))
            pointOnCurveInfo = pm.createNode('pointOnCurveInfo', name='%sneckHead%s_positionOnCurveInfo' % (self.chName, n + 1))
            neckHeadCurve.worldSpace[0].connect(pointOnCurveInfo.inputCurve)
            pointOnCurveInfo.parameter.set(param)
            pointOnCurveInfo.position.connect(jointDriverGrp.translate)
            noXformNeckHeadGrp.addChild(jointDriverGrp)
            # drive joint by a parent constraint
            jointDriverList.append(jointDriverGrp)

            # up vector transforms, useful for later aimContraint
            ObjectUpVector = pm.group(empty=True, name='%s_upVector' % str(joint))
            # ObjectUpVector = pm.spaceLocator(name='%s_upVector' % str(joint))
            ObjectUpVector.setTranslation(jointDriverGrp.getTranslation() + pm.datatypes.Vector(0, 0, -20), 'world')
            noXformNeckHeadGrp.addChild(ObjectUpVector)
            ObjectUpVectorList.append(ObjectUpVector)

            # AimConstraint locators, each locator aim to the upper locator
            if n == 0:
                # parent first target transform, to hips controller
                self.ikControllers['spine'][-1].addChild(ObjectUpVector)
            if n > 0:
                aimConstraint = pm.aimConstraint(jointDriverList[-1], jointDriverList[-2], aimVector=(1, 0, 0),
                                                 upVector=(0, 1, 0), worldUpType='object', worldUpObject=ObjectUpVectorList[-2])

        # parent last target transform, to chest
        neckHeadIKCtrList[-1].addChild(ObjectUpVectorList[-1])

        # review: create parent constraints, once drivers have been created, if not, all flip
        for i in range(len(neckHeadJoints[:-1])):
            pm.parentConstraint(jointDriverList[i], neckHeadJoints[i], maintainOffset=True, name='%s_parentConstraint' % str(joint))

        # connect by pointConstraint objectUpVector to first and last upVectors
        totalDistance = ObjectUpVectorList[-1].getTranslation('world') - ObjectUpVectorList[0].getTranslation('world')
        totalDistance = totalDistance.length()
        for n, upVectorObject in enumerate(ObjectUpVectorList):
            if n == 0 or n == len(ObjectUpVectorList) - 1:
                continue
            distance = upVectorObject.getTranslation('world') - ObjectUpVectorList[0].getTranslation('world')
            distance = distance.length()
            pointConstraintFactor = distance / totalDistance

            pointContraint = pm.pointConstraint(ObjectUpVectorList[-1], ObjectUpVectorList[0], upVectorObject,
                                                maintainOffset=False, name='%s_pointConstraint' % str(upVectorObject))
            pointContraint.attr('%sW0' % str(ObjectUpVectorList[-1])).set(pointConstraintFactor)
            pointContraint.attr('%sW1' % str(ObjectUpVectorList[0])).set(1 - pointConstraintFactor)

        # stretch squash neck
        # curveInfo and connect neckHeadCurve
        curveInfo = pm.createNode('curveInfo', name='%s_neckHeadCurve_curveInfo' %(self.chName))
        neckHeadCurve.worldSpace[0].connect(curveInfo.inputCurve)
        neckHeadCurveLength = neckHeadCurve.length()

        # create anim curve to control scale influence
        # maybe this is better to do with a curveAttr
        scaleInfluenceCurve = pm.createNode('animCurveTU')
        scaleInfluenceCurve.addKeyframe(0, 0.0)
        scaleInfluenceCurve.addKeyframe((len(neckHeadJoints)-1)//2, 1.0)
        scaleInfluenceCurve.addKeyframe(len(neckHeadJoints)-2, 0.0)
        for n, joint in enumerate(neckHeadJoints):
            # for each joint, create a multiply divide node
            # formula for scale: 1+(factorScale - 1)*influence
            # TODO: rename all this
            if re.match('.*tip.*', str(joint)):
                continue
            multiplyDivide = pm.createNode('multiplyDivide')
            multiplyDivide.operation.set(2)
            multiplyDivide.input1X.set(neckHeadCurveLength)
            curveInfo.arcLength.connect(multiplyDivide.input2X)
            plusMinusAverage = pm.createNode('plusMinusAverage')
            multiplyDivide.outputX.connect(plusMinusAverage.input1D[0])
            plusMinusAverage.input1D[1].set(-1)
            multiplyDivideInfluence = pm.createNode('multiplyDivide')
            plusMinusAverage.output1D.connect(multiplyDivideInfluence.input1X)
            # frame cache
            frameCache = pm.createNode('frameCache')
            scaleInfluenceCurve.output.connect(frameCache.stream)
            frameCache.varyTime.set(n)
            frameCache.varying.connect(multiplyDivideInfluence.input2X)
            # plus 1
            plusMinusAverageToJoint = pm.createNode('plusMinusAverage')
            multiplyDivideInfluence.outputX.connect(plusMinusAverageToJoint.input1D[0])
            plusMinusAverageToJoint.input1D[1].set(1)

            # connect to joint
            plusMinusAverageToJoint.output1D.connect(joint.scaleY)
            plusMinusAverageToJoint.output1D.connect(joint.scaleZ)


#######
#utils#
#######
def createRoots(*args):
    roots = []
    for arg in args:
        try:
            parent = arg.firstParent()
        except:
            parent = None
        rootGrp = pm.group(em=True, name='%s_root' % arg)
        rootGrp.setTranslation(arg.getTranslation('world'), 'world')
        if parent:
            parent.addChild(rootGrp)
        rootGrp.addChild(arg)
        roots.append(rootGrp)
    return roots
    
def createController(name, controllerType = 'circle', s=1.0):
    """
    create circle or square controllers
    Args:
    name: name of controller
    controllerType(str): circle, square
    """
    if controllerType == 'circle':
        controller = pm.circle(ch=False, name=name, nr=(0,1,0), r=15 * s)[0]
        controllerShape = controller.getShape()
        controllerShape.attr('overrideEnabled').set(True)
        controllerShape.attr('overrideColor').set(17)
        
    elif controllerType == 'square':
        controller = pm.curve(ep=((-15*s,0*s,15*s), (-15*s,0*s,-15*s), (15*s,0*s,-15*s), (15*s,0*s,15*s), (-15*s,0*s,15*s)), name=name, d=1)
        controllerShape = controller.getShape()
        controllerShape.attr('overrideEnabled').set(True)
        controllerShape.attr('overrideColor').set(4)

    logger.debug('controller %s' % controller)

    return controller