import pymel.core as pm
import re
from maya import OpenMaya
from autoRigTools import ctrSaveLoadToJson

import logging
logging.basicConfig()
logger = logging.getLogger('autoRig:')
logger.setLevel(logging.DEBUG)

class autoRig(object):
    def __init__(self, chName='akona', path='D:\_docs\_Animum\_leccion3\python'):
        """
        autoRig class tools
        """
        # TODO: node 'unknown' messages attributes to store connections?
        self.chName = chName
        self.path = path
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

    # TODO: zone var in names
    def autoSpine(self, zone='spine'):
        """
            Auto create a character spine
        """
        # TODO: check spine list sort, by hierarchy descending
        # detect spine joints and their positions
        spineJoints = [point for point in pm.ls() if re.match('^%s.*((hips)|(spine)|(chest)).*joint$' % self.chName, str(point))]
        positions = [point.getTranslation(space='world') for point in spineJoints]
        logger.debug('Spine joints: %s' % spineJoints)

        spineCurveTransform = pm.curve(ep=positions, name='%s_%s_1_crv' % (self.chName, zone))
        # parent to nXform grp
        noXformSpineGrp = pm.group(empty=True, name='%s_noXform_%s_grp' % (self.chName, zone))
        noXformSpineGrp.inheritsTransform.set(False)
        self.noXformGrp.addChild(noXformSpineGrp)
        noXformSpineGrp.addChild(spineCurveTransform)

        # curve shape node
        spineCurve = spineCurveTransform.getShape()

        #rebuildCurve
        pm.rebuildCurve(spineCurve, s=2, rpo=True, ch=False, rt=0, d=3, kt=0, kr=0)

        # review: test autoMethod
        adjustCurveToPoints(spineJoints, spineCurve, 16, 0.01)

        # create locators and connect to curve CV's
        spineDrvList = []
        spineIKControllerList = []
        spineFKControllerList = []
        for n, point in enumerate(spineCurve.getCVs()):
            ctrType = 'hips' if n == 0 else 'chest' if n == spineCurve.numCVs() - 1 else 'spine%s' % n
            # create grp to manipulate the curve
            spineDriver = pm.group(name='%s_Curve_%s_%s_drv' % (self.chName, zone, ctrType), empty=True)
            spineDriver.setTranslation(point)
            decomposeMatrix = pm.createNode('decomposeMatrix', name='%s_%s_%s_decomposeMatrix' % (self.chName, zone, ctrType))
            spineDriver.worldMatrix[0].connect(decomposeMatrix.inputMatrix)
            decomposeMatrix.outputTranslate.connect(spineCurve.controlPoints[n])
            spineDrvList.append(spineDriver)

            # create controller and parent locator
            # TODO: numeration of controllers is wrong
            spineController = self.createController('%s_IK_%s_%s_1_ctr' % (self.chName, zone, ctrType), '%sIk' % ctrType, 1, 17)
            logger.debug('spine controller: %s' % spineController)

            # try make chest deform more "natural"
            if n == spineCurve.numCVs()-1:
                lastSpineIkController = spineIKControllerList[1].getTranslation('world')
                spineController.setTranslation((lastSpineIkController[0], point[1], lastSpineIkController[2]))
            else:
                spineController.setTranslation(point)

            spineController.addChild(spineDriver)
            spineIKControllerList.append(spineController)

            # spine type controllers only translate, lock unused attr
            if 'spine' in ctrType:
                lockAndHideAttr(spineController, False, True, True)

            # create FK controllers
            if n < 3:
                # first fk controller bigger
                fkCtrSize = 1.5 if len(spineFKControllerList) == 0 else 1
                spineFKController = self.createController('%s_FK_spine_%s_ctr' % (self.chName, n + 1), 'hipsFk', fkCtrSize, 4)
                spineFKController.setTranslation(point)
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
            lockAndHideAttr(neckHeadIKCtr, True, False, False)

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
            jointNameSplit = str(joint).split('_')[1]
            jointDriverGrp = pm.group(empty=True, name='%s_drv_%s_%s_%s_drv' % (self.chName, zone, jointNameSplit, n+1))
            # jointDriverGrp = pm.spaceLocator(name='%s_target' % str(joint))
            pointOnCurveInfo = pm.createNode('pointOnCurveInfo', name='%s_drv_%s_%s_%s_positionOnCurveInfo' % (self.chName, zone, jointNameSplit, n+1))
            spineCurve.worldSpace[0].connect(pointOnCurveInfo.inputCurve)
            pointOnCurveInfo.parameter.set(param)
            pointOnCurveInfo.position.connect(jointDriverGrp.translate)
            noXformSpineGrp.addChild(jointDriverGrp)
            # drive joint by a parent constraint
            jointDriverList.append(jointDriverGrp)

            # up vector transforms, useful for later aimContraint
            ObjectUpVector = pm.group(empty=True, name='%s_drv_%s_%s_%s_upVector' % (self.chName,zone,jointNameSplit, n+1))
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

        # objectUpVector conections, by pointContraint
        totalDistance = ObjectUpVectorList[-1].getTranslation('world') - ObjectUpVectorList[0].getTranslation('world')
        logger.debug('totalDistance: %s' % totalDistance)
        totalDistance = totalDistance.length()
        logger.debug('totalDistance: %s' % totalDistance)

        # can't do this before, because we need de first and the last upVectorObjects to config the pointConstraints
        # connect ipVectorObjects with point constraint
        for n, upVectorObject in enumerate(ObjectUpVectorList):
            if n == 0 or n == len(ObjectUpVectorList)-1:
                continue
            jointNameSplit = str(spineJoints[n]).split('_')[1]
            distance = upVectorObject.getTranslation('world') - ObjectUpVectorList[0].getTranslation('world')
            distance = distance.length()
            pointConstraintFactor = distance/totalDistance

            pointContraint = pm.pointConstraint(ObjectUpVectorList[-1], ObjectUpVectorList[0], upVectorObject, maintainOffset=False, name='%s_drv_%s_%s_upVector_pointConstraint' % (self.chName,zone,jointNameSplit))
            pointContraint.attr('%sW0' % str(ObjectUpVectorList[-1])).set(pointConstraintFactor)
            pointContraint.attr('%sW1' % str(ObjectUpVectorList[0])).set(1-pointConstraintFactor)

        # stretch squash spine
        # curveInfo and connect spineCurve
        curveInfo = pm.createNode('curveInfo', name='%s_stretchSquash_%s_1_curveInfo' % (self.chName, zone))
        spineCurve.worldSpace[0].connect(curveInfo.inputCurve)
        spineCurveLength = spineCurve.length()

        # create anim curve to control scale influence
        # maybe this is better to do with a curveAttr
        scaleInfluenceCurve = pm.createNode('animCurveTU', name='%s_stretchSquash_%s_1_animCurve' % (self.chName, zone))
        scaleInfluenceCurve.addKeyframe(0, 0.0)
        scaleInfluenceCurve.addKeyframe(len(spineJoints)//2, 1.0)
        scaleInfluenceCurve.addKeyframe(len(spineJoints)-1, 0.0)
        for n, joint in enumerate(spineJoints):
            # for each joint, create a multiply divide node
            # formula for scale: 1+(factorScale - 1)*influence
            # TODO: rename all this
            if re.match('.*chest.*', str(joint)):
                continue

            # connect to joints
            # review: create parent constraints, once drivers have been created, if not, all flip
            jointNameSplit = str(joint).split('_')[1]  # review, maybe better store joints name in a list
            pm.parentConstraint(jointDriverList[n], spineJoints[n], maintainOffset=True, name='%s_drv_%s_%s_%s_parentConstraint' % (self.chName, zone, jointNameSplit, n+1))

            # TODO: rename nodes
            multiplyDivide = pm.createNode('multiplyDivide', name='%s_stretchSquash_%s_%s_%s_multiplyDivide' % (self.chName, zone, jointNameSplit, n+1))
            multiplyDivide.operation.set(2)
            multiplyDivide.input1X.set(spineCurveLength)
            curveInfo.arcLength.connect(multiplyDivide.input2X)
            plusMinusAverage = pm.createNode('plusMinusAverage', name='%s_stretchSquash_%s_%s_%s_plusMinusAverage' % (self.chName, zone, jointNameSplit, n+1))
            multiplyDivide.outputX.connect(plusMinusAverage.input1D[0])
            plusMinusAverage.input1D[1].set(-1)
            multiplyDivideInfluence = pm.createNode('multiplyDivide', name='%s_stretchSquash_%s_%s_%s_b_multiplyDivide' % (self.chName, zone, jointNameSplit, n+1))
            plusMinusAverage.output1D.connect(multiplyDivideInfluence.input1X)
            # frame cache
            frameCache = pm.createNode('frameCache', name='%s_stretchSquash_%s_%s_%s_frameCache' % (self.chName, zone, jointNameSplit, n+1))
            scaleInfluenceCurve.output.connect(frameCache.stream)
            frameCache.varyTime.set(n)
            frameCache.varying.connect(multiplyDivideInfluence.input2X)
            # plus 1
            plusMinusAverageToJoint = pm.createNode('plusMinusAverage', name='%s_stretchSquash_%s_%s_%s_b_plusMinusAverage' % (self.chName, zone, jointNameSplit, n+1))
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
        neckHeadJoints = [point for point in pm.ls() if re.match('^%s.*(neck|head).*joint$' % self.chName, str(point))]
        logger.debug('Neck head joints: %s' % neckHeadJoints)
        positions = [point.getTranslation(space='world') for point in neckHeadJoints[:-1]]
        #  positions.append((positions[-1][0],positions[-1][1]+3,positions[-1][2]))  extra point for head

        neckHeadCurveTransform = pm.curve(ep=positions, name='%s_%s_1_crv' % (self.chName, zone))
        # parent to noXform grp
        noXformNeckHeadGrp = pm.group(empty=True, name='%s_noXform_%s_grp' % (self.chName, zone))
        noXformNeckHeadGrp.inheritsTransform.set(False)
        self.noXformGrp.addChild(noXformNeckHeadGrp)
        noXformNeckHeadGrp.addChild(neckHeadCurveTransform)

        neckHeadCurve = neckHeadCurveTransform.getShape()

        # rebuildCurve
        pm.rebuildCurve(neckHeadCurve, s=2, rpo=True, ch=False, rt=0, d=3, kt=0, kr=0)

        # review: testAuto
        # TODO: search an automation, use  distanceToCurve
        adjustCurveToPoints(neckHeadJoints[:-1], neckHeadCurve, 16, 0.01)

        # create locators and connect to curve CV's
        neckHeadDrvList = []
        neckHeadIKCtrList = []
        neckHeadFKCtrList = []

        for n, point in enumerate(neckHeadCurve.getCVs()):
            # create drivers to manipulate the curve
            neckHeadDriver = pm.group(name='%s_Curve_%s_%s_drv' % (self.chName, zone, n+1), empty=True)
            neckHeadDriver.setTranslation(point)
            # use the worldMatrix TODO: rename better no neckhead_3 -> head_1
            decomposeMatrix = pm.createNode('decomposeMatrix', name='%s_%s_%s_decomposeMatrix' % (self.chName,zone, n+1))
            neckHeadDriver.worldMatrix[0].connect(decomposeMatrix.inputMatrix)
            decomposeMatrix.outputTranslate.connect(neckHeadCurve.controlPoints[n])
            # set last ik spine controller as parent
            self.ikControllers['spine'][-1].addChild(neckHeadDriver)
            neckHeadDrvList.append(neckHeadDriver)  # add to drv List

            # no create controller two first drivers and the penultimate
            # TODO: better continue after if
            if n > 1 and not n == neckHeadCurve.numCVs()-2:
                # create controller and parent drivers to controllers
                ctrType = 'neck' if not len(neckHeadIKCtrList) else 'head'
                neckHeadIKCtr = self.createController('%s_IK_%s_%s_1_ctr' % (self.chName, zone, ctrType), '%sIk' % ctrType, 1, 17)
                logger.debug('neckHead controller: %s' % neckHeadIKCtr)

                # try make head deform more "natural"
                if n == neckHeadCurve.numCVs() - 1:
                    lastSpineIkController = neckHeadIKCtrList[-1].getTranslation('world')
                    neckHeadIKCtr.setTranslation((lastSpineIkController[0], point[1], lastSpineIkController[2]))
                else:
                    neckHeadIKCtr.setTranslation(point)

                neckHeadIKCtr.addChild(neckHeadDriver)
                neckHeadIKCtrList.append(neckHeadIKCtr)  # add to ik controller List

                # create FK controllers, only with the first ik controller
                if len(neckHeadIKCtrList) == 1:
                    neckHeadFKCtr = self.createController('%s_FK_%s_%s_1_ctr' % (self.chName, zone, ctrType), 'hipsFk',.5,4)
                    neckHeadFKCtr.setTranslation(point)
                    neckHeadFKCtrList.append(neckHeadFKCtr)
                    # Fk hierarchy, if we have more fk controllers. not the case
                    if len(neckHeadFKCtrList) > 1:
                        neckHeadFKCtrList[n-1].addChild(neckHeadFKCtr)
                        logger.debug('parent %s, child %s' % (neckHeadFKCtrList[-1], neckHeadFKCtr))

        # configure ctr hierarchy
        neckHeadFKCtrList[-1].addChild(neckHeadIKCtrList[-1])
        neckHeadIKCtrList[-1].addChild(neckHeadDrvList[-2])  # add the penultimate driver too
        self.ikControllers['spine'][-1].addChild(neckHeadIKCtrList[0])  # ik controller child of last spine controller
        neckHeadIKCtrList[0].addChild(neckHeadDrvList[1])
        # rename head control
        neckHeadIKCtrList[-1].rename('%s_IK_%s_head_1_ctr' % (self.chName, zone))  # review: better here or above?
        # Fk parent to last ik spine controller
        self.ikControllers['spine'][-1].addChild(neckHeadFKCtrList[-1])

        # create roots grp
        neckHeadFKCtrRoots = createRoots(*neckHeadFKCtrList)
        neckHeadIKCtrRoots = createRoots(*neckHeadIKCtrList)
        # once created roots, we can freeze and hide attributes. if not, it can be unstable
        for neckHeadFKCtr in neckHeadFKCtrList:
            lockAndHideAttr(neckHeadFKCtr, True, False, False)
        # lock and hide neck attr, it's here because we have only one
        lockAndHideAttr(neckHeadIKCtrList[0], False, True, True)

        # head orient auto
        # head orient neck grp
        neckOrientAuto = pm.group(empty=True, name='%s_orientAuto_%s_head_1_grp' % (self.chName, zone))
        neckOrientAuto.setTranslation(neckHeadIKCtrList[-1].getTranslation('world'), 'world')
        neckHeadFKCtrList[-1].addChild(neckOrientAuto)

        headIkAutoGrp = pm.group(empty=True, name='%s_orientAuto_%s_head_ikAuto_1_grp' % (self.chName, zone))
        headIkAutoGrp.setTranslation(neckHeadIKCtrList[-1].getTranslation('world'), 'world')
        neckHeadFKCtrList[-1].addChild(headIkAutoGrp)
        headIkAutoGrp.addChild(neckHeadIKCtrRoots[-1])

        # head orient base grp
        baseOrientAuto = pm.group(empty=True, name='%s_orientAuto_%s_head_base_1_grp' % (self.chName, zone))
        baseOrientAuto.setTranslation(neckOrientAuto.getTranslation('world'), 'world')
        self.ctrGrp.addChild(baseOrientAuto)

        # create driver attr
        pm.addAttr(neckHeadIKCtrList[-1], longName='Isolate', shortName='Isolate', minValue=0.0,
                   maxValue=1.0, type='float', defaultValue=0.0, k=True)

        # constraint head controller offset to orient auto grps
        autoOrientConstraint = pm.parentConstraint(baseOrientAuto, neckOrientAuto, headIkAutoGrp, maintainOffset=False, name='%s_autoOrient_%s_head_1_parentConstraint' % (self.chName, zone))

        # create Nodes and connect
        neckHeadIKCtrList[-1].Isolate.connect(autoOrientConstraint.attr('%sW0' % str(baseOrientAuto)))

        plusMinusAverage = pm.createNode('plusMinusAverage', name='%s_orientAuto_%s_head_isolate_1_plusMinusAverage' % (self.chName, zone))
        neckHeadIKCtrList[-1].Isolate.connect(plusMinusAverage.input1D[1])
        plusMinusAverage.input1D[0].set(1)
        plusMinusAverage.operation.set(2)
        plusMinusAverage.output1D.connect(autoOrientConstraint.attr('%sW1' % str(neckOrientAuto)))

        # create points on curve that will drive the joints
        jointDriverList = []
        ObjectUpVectorList = []
        for n, joint in enumerate(neckHeadJoints[:-1]):
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
            jointNameSplit = str(joint).split('_')[1]
            jointDriverGrp = pm.group(empty=True, name='%s_drv_%s_%s_%s_drv' % (self.chName, zone, jointNameSplit, n+1))
            # jointDriverGrp = pm.spaceLocator(name='%s_target' % str(joint))
            pointOnCurveInfo = pm.createNode('pointOnCurveInfo', name='%s_drv_%s_%s_%s_positionOnCurveInfo' % (self.chName, zone, jointNameSplit, n+1))
            neckHeadCurve.worldSpace[0].connect(pointOnCurveInfo.inputCurve)
            pointOnCurveInfo.parameter.set(param)
            pointOnCurveInfo.position.connect(jointDriverGrp.translate)
            noXformNeckHeadGrp.addChild(jointDriverGrp)
            # drive joint by a parent constraint
            jointDriverList.append(jointDriverGrp)

            # up vector transforms, useful for later aimContraint
            # ObjectUpVector = pm.group(empty=True, name='%s_upVector' % str(joint))
            ObjectUpVector = pm.spaceLocator(name='%s_drv_%s_%s_%s_upVector' % (self.chName,zone,jointNameSplit, n+1))
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

        # connect by pointConstraint objectUpVector from first to last upVectors
        totalDistance = ObjectUpVectorList[-1].getTranslation('world') - ObjectUpVectorList[0].getTranslation('world')
        totalDistance = totalDistance.length()
        for n, upVectorObject in enumerate(ObjectUpVectorList):
            if n == 0 or n == len(ObjectUpVectorList) - 1:
                continue
            distance = upVectorObject.getTranslation('world') - ObjectUpVectorList[0].getTranslation('world')
            distance = distance.length()
            pointConstraintFactor = distance / totalDistance

            pointContraint = pm.pointConstraint(ObjectUpVectorList[-1], ObjectUpVectorList[0], upVectorObject,
                                                maintainOffset=False, name='%s_drv_%s_%s_upVector_pointConstraint' % (self.chName,zone,jointNameSplit))
            pointContraint.attr('%sW0' % str(ObjectUpVectorList[-1])).set(pointConstraintFactor)
            pointContraint.attr('%sW1' % str(ObjectUpVectorList[0])).set(1 - pointConstraintFactor)

        # stretch squash neck
        # curveInfo and connect neckHeadCurve
        curveInfo = pm.createNode('curveInfo', name='%s_stretchSquash_%s_1_curveInfo' % (self.chName, zone))
        neckHeadCurve.worldSpace[0].connect(curveInfo.inputCurve)
        neckHeadCurveLength = neckHeadCurve.length()

        # create anim curve to control scale influence
        # maybe this is better to do with a curveAttr
        scaleInfluenceCurve = pm.createNode('animCurveTU', name='%s_stretchSquash_%s_1_animCurve' % (self.chName, zone))
        scaleInfluenceCurve.addKeyframe(0, 0.0)
        scaleInfluenceCurve.addKeyframe((len(neckHeadJoints)-1)//2, 1.0)
        scaleInfluenceCurve.addKeyframe(len(neckHeadJoints)-2, 0.0)
        for n, joint in enumerate(neckHeadJoints):
            # for each joint, create a multiply divide node
            # formula for scale: 1+(factorScale - 1)*influence
            # TODO: rename all this
            if re.match('.*tip.*', str(joint)):
                continue

            jointNameSplit = str(joint).split('_')[1]
            # review: create parent constraints, once drivers have been created, if not, all flip
            if re.match('.*head.*', str(joint)):
                # head joint, with point to driver, and orient to controller
                pm.pointConstraint(jointDriverList[n], joint, maintainOffset=False, name='%s_drv_%s_%s_%s_pointConstraint' % (self.chName, zone, jointNameSplit, n+1))
                pm.orientConstraint(neckHeadIKCtrList[-1], joint, maintainOffset=True, name='%s_drv_%s_%s_%s_orientConstraint' % (self.chName, zone, jointNameSplit, n+1))

            else:
                pm.parentConstraint(jointDriverList[n], joint, maintainOffset=True, name='%s_drv_%s_%s_%s_parentConstraint' % (self.chName, zone, jointNameSplit, n+1))


            multiplyDivide = pm.createNode('multiplyDivide', name='%s_stretchSquash_%s_%s_%s_multiplyDivide' % (self.chName, zone, jointNameSplit, n+1))
            multiplyDivide.operation.set(2)
            multiplyDivide.input1X.set(neckHeadCurveLength)
            curveInfo.arcLength.connect(multiplyDivide.input2X)
            plusMinusAverage = pm.createNode('plusMinusAverage', name='%s_stretchSquash_%s_%s_%s_plusMinusAverage' % (self.chName, zone, jointNameSplit, n+1))
            multiplyDivide.outputX.connect(plusMinusAverage.input1D[0])
            plusMinusAverage.input1D[1].set(-1)
            multiplyDivideInfluence = pm.createNode('multiplyDivide', name='%s_stretchSquash_%s_%s_%s_b_multiplyDivide' % (self.chName, zone, jointNameSplit, n+1))
            plusMinusAverage.output1D.connect(multiplyDivideInfluence.input1X)
            # frame cache
            frameCache = pm.createNode('frameCache', name='%s_stretchSquash_%s_%s_%s_frameCache' % (self.chName, zone, jointNameSplit, n+1))
            scaleInfluenceCurve.output.connect(frameCache.stream)
            frameCache.varyTime.set(n)
            frameCache.varying.connect(multiplyDivideInfluence.input2X)
            # plus 1
            plusMinusAverageToJoint = pm.createNode('plusMinusAverage', name='%s_stretchSquash_%s_%s_%s_b_plusMinusAverage' % (self.chName, zone, jointNameSplit, n+1))
            multiplyDivideInfluence.outputX.connect(plusMinusAverageToJoint.input1D[0])
            plusMinusAverageToJoint.input1D[1].set(1)

            # connect to joint
            plusMinusAverageToJoint.output1D.connect(joint.scaleY)
            plusMinusAverageToJoint.output1D.connect(joint.scaleZ)

        # save data
        self.joints[zone] = neckHeadJoints
        self.ikControllers[zone] = neckHeadIKCtrList

    def createController(self, name, controllerType, s=1.0, colorIndex=4):
        """
        Args:
        name: name of controller
        controllerType(str): from json controller types
        """
        controller = pm.PyNode(ctrSaveLoadToJson.ctrLoadJson(controllerType, self.chName, self.path, s, colorIndex))
        controller.rename(name)

        logger.debug('controller %s' % controller)
        return controller


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

def lockAndHideAttr(obj, translate=False, rotate=False, scale=False):
    if translate:
        obj.translate.lock()
        for axis in ('X', 'Y', 'Z'):
            pm.setAttr('%s.translate%s' % (str(obj), axis), channelBox=False, keyable=False)
    if rotate:
        obj.rotate.lock()
        for axis in ('X', 'Y', 'Z'):
            pm.setAttr('%s.rotate%s' % (str(obj), axis), channelBox=False, keyable=False)
    if scale:
        obj.scale.lock()
        for axis in ('X', 'Y', 'Z'):
            pm.setAttr('%s.scale%s' % (str(obj), axis), channelBox=False, keyable=False)


def adjustCurveToPoints(joints, curve, iterations=4, precision=0.05):
    selection = OpenMaya.MSelectionList()
    selection.add(str(curve))
    dagpath = OpenMaya.MDagPath()
    selection.getDagPath(0, dagpath)

    mfnNurbsCurve = OpenMaya.MFnNurbsCurve(dagpath)

    for i in range(iterations):
        for joint in joints:
            jointPos = joint.getTranslation('world')
            jointPosArray = OpenMaya.MFloatArray()
            util = OpenMaya.MScriptUtil()
            util.createFloatArrayFromList(jointPos, jointPosArray)

            mPoint = OpenMaya.MPoint(jointPosArray[0], jointPosArray[1], jointPosArray[2], 1)
            closestPointCurve = mfnNurbsCurve.closestPoint(mPoint, None, 1, OpenMaya.MSpace.kWorld)

            mvector = OpenMaya.MVector(mPoint - closestPointCurve)

            if mvector.length() < precision:
                continue

            # nearest cv
            cvArray = OpenMaya.MPointArray()
            mfnNurbsCurve.getCVs(cvArray, OpenMaya.MSpace.kWorld)
            nearest = []
            lastDistance = None

            for n in range(mfnNurbsCurve.numCVs()):
                if n == 0 or n == cvArray.length() - 1:
                    continue

                distance = mPoint.distanceTo(cvArray[n])

                if not nearest or distance < lastDistance:
                    nearest = []
                    nearest.append(cvArray[n])
                    nearest.append(n)

                    lastDistance = distance

            mfnNurbsCurve.setCV(nearest[1], nearest[0] + mvector, OpenMaya.MSpace.kWorld)

    mfnNurbsCurve.updateCurve()