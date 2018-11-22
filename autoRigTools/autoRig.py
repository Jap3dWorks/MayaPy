import pymel.core as pm
import re
from maya import OpenMaya
from autoRigTools import ctrSaveLoadToJson
import inspect
reload(ctrSaveLoadToJson)  # review: reload

import logging
logging.basicConfig()
logger = logging.getLogger('autoRig:')
logger.setLevel(logging.DEBUG)

# TODO: neck twist odd, skinning problem?

class RigAuto(object):

    def __init__(self, chName, path):
        """
        autoRig class tools
        """
        # TODO: create node Module 'unknown' or chName_rig_grp transform node with messages attributes to store connections
        self.chName = chName
        self.path = path
        self.joints = {}  # store joints
        self.ikControllers = {}
        self.fkControllers = {}
        self.ikHandles = {}

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

        self.methodNames = [x[0] for x in inspect.getmembers(self, predicate=inspect.ismethod) if 'auto' in x[0]]
        print (self.methodNames)

    # method decorator, check if already exist the rig part,
    # and create the necessary attr circuity (nodes with controllers connections)
    class checker_auto(object):
        def __init__(self, decorated):
            # TODO: do not understand why i need to make this
            self._decorated = decorated

        def __call__(self, func):
            # store func name
            # here we have the zone defined
            funcName = func.__name__.replace('_auto', '')
            # start wrapper
            def wrapper(*args, **kwargs):
                # check if node exist
                # check if side is in args
                chName = args[0].chName  # explanation: acces outher class attributes
                sideCheck = 'left' if 'left' in args else 'right' if 'right' in args else None
                sideCheck = kwargs['side'] if 'side' in kwargs else sideCheck

                moduleSide = '%s_module' % sideCheck if sideCheck else 'module'
                nodeName = '%s_%s_%s' % (chName, funcName, moduleSide)  # name of the desired node
                # check if module allready exists
                try:
                    moduleNode = pm.PyNode(nodeName)
                except:
                    moduleNode = None

                if moduleNode:
                    logger.debug('%s %s module exist yet' % (nodeName))
                    return None

                # if module does not exist, run method
                # also get info to construct the necessary nodes
                totalControlList = func(*args, **kwargs)

                # create unknown node
                connectionTypes = ['ikControllers', 'fkControllers']
                moduleNode = pm.createNode('script', name=nodeName)
                pm.addAttr(moduleNode, ln='module', sn='module', attributeType='message')
                for connection in connectionTypes:
                    pm.addAttr(moduleNode, ln=connection, sn=connection,  attributeType='message')

                for i, ctrType in enumerate(connectionTypes):
                    for ctr in totalControlList[i]:
                        pm.addAttr(ctr, ln='module', sn='module', attributeType='message')
                        moduleNode.attr(ctrType).connect(ctr.module)

                # connect to parent module
                # if not exist yet, create
                try:
                    chModule = pm.PyNode('%s' % chName)
                except:
                    raise ValueError('Do not found %s elements' % chName)

                # check connections
                if not chModule.hasAttr(funcName):
                    pm.addAttr(chModule, ln=funcName, sn=funcName, attributeType='message')

                chModule.attr(funcName).connect(moduleNode.module)


                return totalControlList

            return wrapper


    # TODO: zone var in names
    @checker_auto('decorated')
    def spine_auto(self, zone='spine'):
        """
            Auto create a character spine
        """
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
            spineController = self.create_controller('%s_ik_%s_%s_1_ctr' % (self.chName, zone, ctrType), '%sIk' % ctrType, 1, 17)
            logger.debug('spine controller: %s' % spineController)

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
                spineFKController = self.create_controller('%s_fk_spine_%s_ctr' % (self.chName, n + 1), 'hipsFk', fkCtrSize, 4)
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
        createRoots(spineFKControllerList)
        spineControllerRootsList = createRoots(spineIKControllerList)

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

            # index to assign upVector Object
            objUpVectorIndex = -1
            # up vector transforms, useful for later aimContraint
            if not n ==len(spineJoints)-1:
                ObjectUpVector = pm.group(empty=True, name='%s_drv_%s_%s_%s_upVector' % (self.chName,zone,jointNameSplit, n+1))
                # ObjectUpVector = pm.spaceLocator(name='%s_upVector' % str(joint))
                ObjectUpVector.setTranslation(jointDriverGrp.getTranslation() + pm.datatypes.Vector(0, 0, -20), 'world')
                noXformSpineGrp.addChild(ObjectUpVector)
                ObjectUpVectorList.append(ObjectUpVector)
                # if not last iteration index -1
                objUpVectorIndex = -2
            # AimConstraint locators, each locator aim to the upper locator
            if n == 0:
                # parent first ObjectUpVector, to hips controller
                spineIKControllerList[0].addChild(ObjectUpVector)
            else:
                aimConstraint = pm.aimConstraint(jointDriverList[-1], jointDriverList[-2], aimVector=(1,0,0), upVector=(0,1,0), worldUpType='object', worldUpObject=ObjectUpVectorList[objUpVectorIndex])


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

            jointNameSplit = str(joint).split('_')[1]  # review, maybe better store joints name in a list

            if re.match('.*(end|hips).*', str(joint)):
                pm.pointConstraint(jointDriverList[n], joint, maintainOffset=False,
                                    name='%s_drv_%s_%s_1_parentConstraint' % (
                                        self.chName, zone, jointNameSplit))
                endJointOrientConstraint = pm.orientConstraint(spineIKControllerList[min(n, len(spineIKControllerList)-1)], joint, maintainOffset=True, name='%s_drv_%s_%s_1_orientConstraint' % (self.chName, zone, jointNameSplit))
                endJointOrientConstraint.interpType.set(0)
                if 'end' in str(joint):
                    continue
            else:
                # connect to joints
                # review: create parent constraints, once drivers have been created, if not, all flip
                pm.parentConstraint(jointDriverList[n], joint, maintainOffset=True,
                                    name='%s_drv_%s_%s_1_parentConstraint' % (
                                    self.chName, zone, jointNameSplit))

            # TODO: rename nodes
            multiplyDivide = pm.createNode('multiplyDivide', name='%s_stretchSquash_%s_%s_1_multiplyDivide' % (self.chName, zone, jointNameSplit))
            multiplyDivide.operation.set(2)
            multiplyDivide.input1X.set(spineCurveLength)
            curveInfo.arcLength.connect(multiplyDivide.input2X)
            plusMinusAverage = pm.createNode('plusMinusAverage', name='%s_stretchSquash_%s_%s_1_plusMinusAverage' % (self.chName, zone, jointNameSplit))
            multiplyDivide.outputX.connect(plusMinusAverage.input1D[0])
            plusMinusAverage.input1D[1].set(-1)
            multiplyDivideInfluence = pm.createNode('multiplyDivide', name='%s_stretchSquash_%s_%s_2_multiplyDivide' % (self.chName, zone, jointNameSplit))
            plusMinusAverage.output1D.connect(multiplyDivideInfluence.input1X)
            # frame cache
            frameCache = pm.createNode('frameCache', name='%s_stretchSquash_%s_%s_frameCache' % (self.chName, zone, jointNameSplit))
            scaleInfluenceCurve.output.connect(frameCache.stream)
            frameCache.varyTime.set(n)
            frameCache.varying.connect(multiplyDivideInfluence.input2X)
            # plus 1
            plusMinusAverageToJoint = pm.createNode('plusMinusAverage', name='%s_stretchSquash_%s_%s_2_plusMinusAverage' % (self.chName, zone, jointNameSplit))
            multiplyDivideInfluence.outputX.connect(plusMinusAverageToJoint.input1D[0])
            plusMinusAverageToJoint.input1D[1].set(1)

            # connect to joint
            plusMinusAverageToJoint.output1D.connect(joint.scaleY)
            plusMinusAverageToJoint.output1D.connect(joint.scaleZ)

    # save data
        self.joints[zone] = spineJoints
        self.ikControllers[zone] = spineIKControllerList
        self.fkControllers[zone] = spineFKControllerList
        return spineIKControllerList, spineFKControllerList

    @checker_auto('decorated')
    def neckHead_auto(self, zone='neckHead'):
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
        adjustCurveToPoints(neckHeadJoints[:-1], neckHeadCurve, 16, 0.01)

        # create locators and connect to curve CV's
        neckHeadDrvList = []
        neckHeadIKCtrList = []
        neckHeadFKCtrList = []

        for n, point in enumerate(neckHeadCurve.getCVs()):
            # create drivers to manipulate the curve
            neckHeadDriver = pm.group(name='%s_curve_%s_%s_drv' % (self.chName, zone, n+1), empty=True)
            neckHeadDriver.setTranslation(point)
            # use the worldMatrix
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
                neckHeadIKCtr = self.create_controller('%s_IK_%s_%s_1_ctr' % (self.chName, zone, ctrType), '%sIk' % ctrType, 1, 17)
                logger.debug('neckHead controller: %s' % neckHeadIKCtr)

                if n == neckHeadCurve.numCVs() - 1:  # las iteration
                    lastSpineIkController = neckHeadIKCtrList[-1].getTranslation('world')
                    neckHeadIKCtr.setTranslation((point[0], point[1], point[2]))
                else:
                    neckHeadIKCtr.setTranslation(neckHeadJoints[1].getTranslation('world'), 'world')  # controller and joint same position

                neckHeadIKCtr.addChild(neckHeadDriver)
                neckHeadIKCtrList.append(neckHeadIKCtr)  # add to ik controller List

                # create FK controllers, only with the first ik controller
                if len(neckHeadIKCtrList) == 1:
                    neckHeadFKCtr = self.create_controller('%s_FK_%s_%s_1_ctr' % (self.chName, zone, ctrType), 'neckFk1',1,4)
                    neckHeadFKCtr.setTranslation(neckHeadJoints[0].getTranslation('world'), 'world')
                    neckHeadFKCtrList.append(neckHeadFKCtr)

                    neckHeadFKCtr2 = self.create_controller('%s_FK_%s_%s_2_ctr' % (self.chName, zone, ctrType), 'neckFk', 1, 4)
                    neckHeadFKCtr2.setTranslation(neckHeadJoints[1].getTranslation('world'), 'world')
                    neckHeadFKCtrList.append(neckHeadFKCtr2)
                    # create hierarchy
                    neckHeadFKCtr.addChild(neckHeadFKCtr2)
                    neckHeadFKCtr2.addChild(neckHeadIKCtr)

                    # Fk hierarchy, if we have more fk controllers. not the case TODO: more procedural
                    if len(neckHeadFKCtrList) > 2:
                        neckHeadFKCtrList[n-1].addChild(neckHeadFKCtr)
                        logger.debug('parent %s, child %s' % (neckHeadFKCtrList[-1], neckHeadFKCtr))

        # configure ctr hierarchy
        neckHeadFKCtrList[-1].addChild(neckHeadIKCtrList[-1])
        neckHeadIKCtrList[-1].addChild(neckHeadDrvList[-2])  # add the penultimate driver too
        #self.ikControllers['spine'][-1].addChild(neckHeadIKCtrList[0])  # ik controller child of last spine controller
        neckHeadIKCtrList[0].addChild(neckHeadDrvList[1])
        # rename head control
        neckHeadIKCtrList[-1].rename('%s_IK_%s_head_1_ctr' % (self.chName, zone))  # review: better here or above?
        # Fk parent to last ik spine controller
        self.ikControllers['spine'][-1].addChild(neckHeadFKCtrList[0])

        # create roots grp
        neckHeadFKCtrRoots = createRoots(neckHeadFKCtrList)
        neckHeadIKCtrRoots = createRoots(neckHeadIKCtrList)
        # once created roots, we can freeze and hide attributes. if not, it can be unstable
        for neckHeadFKCtr in neckHeadFKCtrList:
            lockAndHideAttr(neckHeadFKCtr, True, False, False)
        # lock and hide neck attr, it's here because we have only one
        lockAndHideAttr(neckHeadIKCtrList[0], False, True, True)

        # head orient auto, isolate
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
        pm.addAttr(neckHeadIKCtrList[-1], longName='isolateOrient', shortName='isolateOrient', minValue=0.0,
                   maxValue=1.0, type='float', defaultValue=0.0, k=True)
        pm.addAttr(neckHeadIKCtrList[-1], longName='isolatePoint', shortName='isolatePoint', minValue=0.0,
                   maxValue=1.0, type='float', defaultValue=0.0, k=True)

        # constraint head controller offset to orient auto grps
        autoOrientConstraint = pm.orientConstraint(baseOrientAuto, neckOrientAuto, headIkAutoGrp, maintainOffset=False, name='%s_autoOrient_%s_head_1_orientConstraint' % (self.chName, zone))
        autoPointConstraint = pm.pointConstraint(baseOrientAuto, neckOrientAuto, headIkAutoGrp, maintainOffset=False, name='%s_autoOrient_%s_head_1_pointConstraint' % (self.chName, zone))

        # create Nodes and connect
        neckHeadIKCtrList[-1].isolateOrient.connect(autoOrientConstraint.attr('%sW0' % str(baseOrientAuto)))
        neckHeadIKCtrList[-1].isolatePoint.connect(autoPointConstraint.attr('%sW0' % str(baseOrientAuto)))

        plusMinusAverageOrient = pm.createNode('plusMinusAverage', name='%s_orientAuto_%s_head_isolateOrient_1_plusMinusAverage' % (self.chName, zone))
        plusMinusAveragepoint = pm.createNode('plusMinusAverage', name='%s_pointAuto_%s_head_isolateOrient_1_plusMinusAverage' % (self.chName, zone))
        neckHeadIKCtrList[-1].isolateOrient.connect(plusMinusAverageOrient.input1D[1])
        neckHeadIKCtrList[-1].isolatePoint.connect(plusMinusAveragepoint.input1D[1])

        plusMinusAverageOrient.input1D[0].set(1)
        plusMinusAveragepoint.input1D[0].set(1)
        plusMinusAverageOrient.operation.set(2)
        plusMinusAveragepoint.operation.set(2)
        plusMinusAverageOrient.output1D.connect(autoOrientConstraint.attr('%sW1' % str(neckOrientAuto)))
        plusMinusAveragepoint.output1D.connect(autoPointConstraint.attr('%sW1' % str(neckOrientAuto)))

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
            ObjectUpVector = pm.group(empty=True, name='%s_upVector' % str(joint))
            # ObjectUpVector = pm.spaceLocator(name='%s_drv_%s_%s_%s_upVector' % (self.chName,zone,jointNameSplit, n+1))
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
                pm.pointConstraint(jointDriverList[n], joint, maintainOffset=False, name='%s_drv_%s_%s_1_pointConstraint' % (self.chName, zone, jointNameSplit))
                pm.orientConstraint(neckHeadIKCtrList[-1], joint, maintainOffset=True, name='%s_drv_%s_%s_1_orientConstraint' % (self.chName, zone, jointNameSplit))

            else:
                pm.parentConstraint(jointDriverList[n], joint, maintainOffset=True, name='%s_drv_%s_%s_1_parentConstraint' % (self.chName, zone, jointNameSplit))

            multiplyDivide = pm.createNode('multiplyDivide', name='%s_stretchSquash_%s_%s_1_multiplyDivide' % (self.chName, zone, jointNameSplit))
            multiplyDivide.operation.set(2)
            multiplyDivide.input1X.set(neckHeadCurveLength)
            curveInfo.arcLength.connect(multiplyDivide.input2X)
            plusMinusAverage = pm.createNode('plusMinusAverage', name='%s_stretchSquash_%s_%s_1_plusMinusAverage' % (self.chName, zone, jointNameSplit))
            multiplyDivide.outputX.connect(plusMinusAverage.input1D[0])
            plusMinusAverage.input1D[1].set(-1)
            multiplyDivideInfluence = pm.createNode('multiplyDivide', name='%s_stretchSquash_%s_%s_2_multiplyDivide' % (self.chName, zone, jointNameSplit))
            plusMinusAverage.output1D.connect(multiplyDivideInfluence.input1X)
            # frame cache
            frameCache = pm.createNode('frameCache', name='%s_stretchSquash_%s_%s_1_frameCache' % (self.chName, zone, jointNameSplit))
            scaleInfluenceCurve.output.connect(frameCache.stream)
            frameCache.varyTime.set(n)
            frameCache.varying.connect(multiplyDivideInfluence.input2X)
            # plus 1
            plusMinusAverageToJoint = pm.createNode('plusMinusAverage', name='%s_stretchSquash_%s_%s_2_plusMinusAverage' % (self.chName, zone, jointNameSplit))
            multiplyDivideInfluence.outputX.connect(plusMinusAverageToJoint.input1D[0])
            plusMinusAverageToJoint.input1D[1].set(1)

            # connect to joint
            plusMinusAverageToJoint.output1D.connect(joint.scaleY)
            plusMinusAverageToJoint.output1D.connect(joint.scaleZ)

        # save data
        self.joints[zone] = neckHeadJoints
        self.ikControllers[zone] = neckHeadIKCtrList
        self.fkControllers[zone] = neckHeadFKCtrList
        return neckHeadIKCtrList, neckHeadFKCtrList

    @checker_auto('decorated')
    def leg_auto(self, side, footAuto, zone='leg'):
        """
        # TODO: zone out of args? read from method?
        # TODO: organize and optimize this method
        auto build a ik fk leg
        Args:
            side: left or right
            zone: leg
        """
        fkColor = 14 if side =='left' else 29
        legJoints = [point for point in pm.ls() if re.match('^%s.*([lL]eg).*%s.*joint$' % (self.chName, side), str(point))]
        logger.debug('%s joints: %s' % (side, legJoints))

        # fk controllers are copies of leg joints
        # save controllers name
        legFkControllersList = []
        legIkControllerList = []
        legMainJointList = []
        legIkJointList = []

        NameIdList = []  # store idNames. p.e upperLeg, lowerLeg

        # duplicate joints
        for i in legJoints:
            controllerName = str(i).split('_')[1] if 'end' not in str(i) else 'end'  # if is a end joint, rename end
            legFkControllersList.append(i.duplicate(po=True, name='%s_fk_%s_%s_%s_ctr' % (self.chName, zone, side, controllerName))[0])
            legIkJointList.append(i.duplicate(po=True, name='%s_ik_%s_%s_%s_joint' % (self.chName, zone, side, controllerName))[0])
            legMainJointList.append(i.duplicate(po=True, name='%s_main_%s_%s_%s_joint' % (self.chName, zone, side, controllerName))[0])
            NameIdList.append(controllerName)

        # reconstruct hierarchy
        # create Fk control shapes
        for i, fkCtr in enumerate(legFkControllersList[:-1]):  # last controller does not has shape
            # ik hierarchy
            legIkJointList[i].addChild(legIkJointList[i + 1])
            # main hierarchy
            legMainJointList[i].addChild(legMainJointList[i+1])

            fkCtr.addChild(legFkControllersList[i+1])
            # fk controls
            shapeFkTransform = self.create_controller('%sShape' % str(fkCtr), '%sFk_%s' % (NameIdList[i], side), 1, fkColor)
            # parentShape
            fkCtr.addChild(shapeFkTransform.getShape(), s=True, r=True)
            # delete shape transform
            pm.delete(shapeFkTransform)

        # ik control
        legIkControl = self.create_controller('%s_ik_%s_%s_ctr' % (self.chName, zone, side), '%sIk_%s' % (zone, side), 1, 17)
        # pm.xform(legIkControl, ws=True, m=pm.xform(legJoints[-1], q=True, ws=True, m=True))
        legIkControl.setTranslation(legJoints[-1].getTranslation('world'), 'world')
        self.ctrGrp.addChild(legIkControl)  # parent to ctr group

        # organitze outliner
        self.ikControllers['spine'][0].addChild(legFkControllersList[0])
        self.ikControllers['spine'][0].addChild(legMainJointList[0])
        self.ikControllers['spine'][0].addChild(legIkJointList[0])

        # save to list
        legIkControllerList.append(legIkControl)
        createRoots(legIkControllerList)

        # fkRoots
        createRoots(legFkControllersList)
        createRoots(legFkControllersList, 'auto')

        # set preferred angle
        legIkJointList[1].preferredAngleZ.set(-15)
        # ik solver
        ikHandle, ikEffector = pm.ikHandle(startJoint=legIkJointList[0], endEffector=legIkJointList[-1], solver='ikRPsolver', name='%s_ik_%s_%s_handle' % (self.chName, zone, side))
        ikEffector.rename('%s_ik_%s_%s_effector' % (self.chName, zone, side))
        legIkControl.addChild(ikHandle)
        # create poles
        legPoleController = self.create_controller('%s_ik_%s_%s_pole_ctr' % (self.chName, zone, side), 'pole')
        relocatePole(legPoleController, legIkJointList, 35)  # relocate pole Vector
        self.ctrGrp.addChild(legPoleController)
        pm.addAttr(legPoleController, ln='polePosition', at='enum', en="world:root:foot", k=True)
        # save poleVector
        legIkControllerList.append(legPoleController)

        # constraint poleVector
        pm.poleVectorConstraint(legPoleController, ikHandle)

        # root poleVector
        legPoleVectorAuto = createRoots([legPoleController])
        createRoots([legPoleController])

        # TODO: abstract more
        # poleVectorAttributes
        poleAttrgrp=[]
        legPoleAnimNodes=[]
        for attr in ('world', 'root', 'foot'):
            legPoleGrp = pm.group(empty=True, name= '%s_ik_%s_%s_pole%s_grp' % (self.chName, zone, attr.capitalize(), side))
            poleAttrgrp.append(legPoleGrp)
            pm.xform(legPoleGrp, ws=True, m=pm.xform(legPoleVectorAuto, ws=True, m=True, q=True))
            legPoleAnim = pm.createNode('animCurveTU', name='%s_ik_%s_%s_pole%s_animNode' % (self.chName, zone, attr.capitalize(), side))
            legPoleController.attr('polePosition').connect(legPoleAnim.input)
            legPoleAnimNodes.append(legPoleAnim)

            if attr == 'world':
                legPoleAnim.addKeyframe(0, 1)
                legPoleAnim.addKeyframe(1, 0)
                legPoleAnim.addKeyframe(2, 0)
                self.ctrGrp.addChild(legPoleGrp)
            elif attr == 'root':
                legPoleAnim.addKeyframe(0, 0)
                legPoleAnim.addKeyframe(1, 1)
                legPoleAnim.addKeyframe(2, 0)
                self.fkControllers['spine'][0].addChild(legPoleGrp)
            elif attr == 'foot':
                legPoleAnim.addKeyframe(0, 0)
                legPoleAnim.addKeyframe(1, 0)
                legPoleAnim.addKeyframe(2, 1)
                legIkControl.addChild(legPoleGrp)

        # once node are created, connect them
        polegrpsParentCnstr=pm.parentConstraint(poleAttrgrp[0],poleAttrgrp[1],poleAttrgrp[2], legPoleVectorAuto, maintainOffset=False, name='%s_pointConstraint' % legPoleVectorAuto)
        for i, poleAttr in enumerate(poleAttrgrp):
            legPoleAnimNodes[i].output.connect(polegrpsParentCnstr.attr('%sW%s' % (str(poleAttr), i)))


        # main blending
        # unknown node to store blend info
        # locator shape instanced version
        ikFkNode = pm.spaceLocator(name='%s_%s_%s_attr' % (self.chName, zone, side))
        ikFkshape = ikFkNode.getShape()
        ikFkshape.visibility.set(0)
        pm.addAttr(ikFkshape, longName='ikFk', shortName='ikFk', minValue=0.0, maxValue=1.0, type='float', defaultValue=1.0, k=True)
        # hide unused attributes
        for attr in ('localPosition', 'localScale'):
            for axis in ('X', 'Y', 'Z'):
                pm.setAttr('%s.%s%s' % (ikFkshape, attr, axis), channelBox=False, keyable=False)

        plusMinusIkFk = pm.createNode('plusMinusAverage', name='%s_ikFk_blending_%s_%s_plusMinusAverage' % (self.chName, zone, side))
        ikFkshape.ikFk.connect(plusMinusIkFk.input1D[1])
        plusMinusIkFk.input1D[0].set(1)
        plusMinusIkFk.operation.set(2)

        # iterate along main joints
        # todo: visibility, connect to ikFkShape
        for i, joint in enumerate(legMainJointList):
            # attributes
            orientConstraint = pm.orientConstraint(legIkJointList[i], legFkControllersList[i], joint, maintainOffset=False, name='%s_main_blending_%s_%s_orientConstraint' % (self.chName, zone, side))
            ikFkshape.ikFk.connect(orientConstraint.attr('%sW0' % str(legIkJointList[i])))
            ikFkshape.ikFk.connect(legIkJointList[i].visibility)

            # parent shape
            legFkControllersList[i].addChild(ikFkshape, s=True, add=True)

            plusMinusIkFk.output1D.connect(orientConstraint.attr('%sW1' % str(legFkControllersList[i])))
            # review: visibility shape
            plusMinusIkFk.output1D.connect(legFkControllersList[i].visibility)

            lockAndHideAttr(legFkControllersList[i], True, False, False)
            pm.setAttr('%s.radi' % legFkControllersList[i], channelBox=False, keyable=False)

            # connect to deform skeleton
            parentConstraint = pm.orientConstraint(joint, legJoints[i], maintainOffset=False, name='%s_main_%s_%s_parentConstraint' % (self.chName, zone, side))

        # ik blending controller attr
        ikFkshape.ikFk.connect(legPoleController.visibility)
        ikFkshape.ikFk.connect(legIkControl.visibility)

        def foot_auto(side, zone='foot'):
            """
            # TODO: organitze and optimize this Func
            auto build a ik fk foot
            Args:
                side: left or right
                zone: foot
            """
            fkColor = 14 if side =='left' else 29
            footJoints = [point for point in pm.ls() if re.match('^%s.*([fF]oot).*%s.*joint$' % (self.chName, side), str(point))]
            toesJoints = [point for point in pm.ls() if re.match('^%s.*([tT]oe).(?!_tip).*%s.*joint$' % (self.chName, side), str(point))]
            footTotalJoints = footJoints + toesJoints
            logger.debug('foot joints: %s' % footJoints)
            logger.debug('toes joints: %s' % toesJoints)

            # arrange toes by joint chain p.e [[toea, toesa_Tip], [toeb, toeb_tip]]
            toesJointsCopy = list(toesJoints)  # copy of the toes list
            toesJointsArr = []
            while len(toesJointsCopy):
                toeJoint = []
                firstJoint = toesJointsCopy.pop(0)
                toeJoint.append(firstJoint)
                for joint in firstJoint.listRelatives(ad=True):
                    if joint in toesJointsCopy:
                        toeJoint.append(joint)
                        toesJointsCopy.remove(joint)

                toesJointsArr.append(toeJoint)

            # controllers and main lists
            footFkControllerList = []  # fk
            toesFkControllerList = []
            footIkControllerList = []  # ik
            toesIkControllerList = []
            footMainJointsList = []  # main
            toesMainJointsList = []
            # create foot ctr

            for joint in footJoints:
                controllerName = str(joint).split('_')[1]
                logger.debug('foot controller name: %s' % controllerName)
                footFkCtr = joint.duplicate(po=True, name='%s_fk_%s_%s_%s_ctr' % (self.chName, zone, side, controllerName))[0]
                footMain = joint.duplicate(po=True, name='%s_main_%s_%s_%s_joint' % (self.chName, zone, side, controllerName))[0]

                # get transformMatrix and orient new controller
                matrix = pm.xform(footFkCtr, ws=True, q=True, m=True)

                vectorX = OpenMaya.MVector(matrix[0], 0, matrix[1])
                vectorX.normalize()
                vectorZ = OpenMaya.MVector(matrix[8], 0, matrix[10])
                vectorZ.normalize()
                vectorY = vectorX ^ vectorZ
                vectorY.normalize()
                vectorX = vectorY ^ vectorZ
                vectorX.normalize()

                matrix = [vectorX.x, vectorX.y, vectorX.z, matrix[3], vectorY.x, vectorY.y, vectorY.z, matrix[7],
                                     vectorZ.x, vectorZ.y, vectorZ.z, matrix[11], matrix[12], matrix[13], matrix[14], matrix[15]]
                pm.xform(footFkCtr, ws=True, m=matrix)  # new transform matrix with vector ajust

                if not footFkControllerList:
                    # create empty grp, useful for ikFk snap
                    fkSyncGrp = pm.group(empty=True, name='%s_fkSync' % str(footFkCtr))
                    pm.xform(fkSyncGrp, ws=True, m=matrix)
                    # parent with main
                    footMain.addChild(fkSyncGrp)


                # fk control Shape
                shape = self.create_controller('%sShape' % str(footFkCtr), '%sFk_%s' % (controllerName, side), 1, fkColor)
                footFkCtr.addChild(shape.getShape(), s=True, r=True)
                pm.delete(shape)

                if not footFkControllerList:
                    # save this matrix, to apply latter if necessary
                    firstfootFkMatrix = matrix

                else:  # if more than 1 joint, reconstruct hierarchy
                    footFkControllerList[-1].addChild(footFkCtr)
                    footMainJointsList[-1].addChild(footMain)

                #save controllers
                footFkControllerList.append(footFkCtr)
                footMainJointsList.append(footMain)

            # parent fk controller under leg
            legFkControllersList[-1].addChild(footFkControllerList[0])
            legMainJointList[-1].addChild(footMainJointsList[0])

            # create toe Fk and ik ctr
            # last foot fkCtr, easiest fot later access
            toeIkCtrParents = []  # list with first joint of toes chains
            for i, toe in enumerate(toesJointsArr):
                toeFkChain = []
                toeIkChain = []
                toeMainChain = []
                for joint in toe:
                    controllerName = str(joint).split('_')[1]
                    logger.debug('foot controller name: %s' % controllerName)
                    toeFkCtr = joint.duplicate(po=True, name='%s_fk_%s_%s_%s_ctr' % (self.chName, zone, side, controllerName))[0]
                    toeMainJnt = joint.duplicate(po=True, name='%s_main_%s_%s_%s_joint' % (self.chName, zone, side, controllerName))[0]
                    toeIkCtr = joint.duplicate(po=True, name='%s_ik_%s_%s_%s_ctr' % (self.chName, zone, side, controllerName))[0]

                    # get transformMatrix and orient new controller
                    matrix = pm.xform(toeFkCtr, ws=True, q=True, m=True)
                    vectorX = OpenMaya.MVector(matrix[0], 0, matrix[1])
                    vectorX.normalize()
                    vectorZ = OpenMaya.MVector(matrix[8], 0, matrix[10])
                    vectorZ.normalize()
                    vectorY = vectorX ^ vectorZ
                    vectorY.normalize()
                    vectorX = vectorY ^ vectorZ
                    vectorX.normalize()
                    matrix = [vectorX.x, vectorX.y, vectorX.z, matrix[3], vectorY.x, vectorY.y, vectorY.z, matrix[7],
                                vectorZ.x, vectorZ.y, vectorZ.z, matrix[11], matrix[12], matrix[13], matrix[14], matrix[15]]
                    # apply transforms constrollers
                    pm.xform(toeFkCtr, ws=True, m=matrix)
                    pm.xform(toeIkCtr, ws=True, m=matrix)

                    # fk ik toe control Shape
                    shape = self.create_controller('%sShape' % str(toeFkCtr), '%sFk' % (controllerName), 1, fkColor)
                    toeFkCtr.addChild(shape.getShape(), s=True, r=True)
                    pm.delete(shape)
                    shape = self.create_controller('%sShape' % str(toeIkCtr), '%sFk' % (controllerName), 1, fkColor)
                    toeIkCtr.addChild(shape.getShape(), s=True, r=True)
                    pm.delete(shape)

                    # if joint Chain, reconstruct hierarchy
                    if toeFkChain:
                        toeFkChain[-1].addChild(toeFkCtr)
                        toeIkChain[-1].addChild(toeIkCtr)
                        toeMainChain[-1].addChild(toeMainJnt)

                    toeFkChain.append(toeFkCtr)
                    toeIkChain.append(toeIkCtr)
                    toeMainChain.append(toeMainJnt)

                    toesFkControllerList.append(toeFkCtr)
                    toesIkControllerList.append(toeIkCtr)
                    toesMainJointsList.append(toeMainJnt)

                # middle toe, useful later to general toe controller
                if i == len(toesJointsArr) // 2:
                    middleToeCtr = toeFkChain[0]
                    middleToeCtrMatrix = pm.xform(middleToeCtr, q=True, ws=True, m=True)

                # construct foot hierarchy
                footFkControllerList[-1].addChild(toeFkChain[0])
                toeIkCtrParents.append(toeIkChain[0])  # ik ctr parent for later
                logger.debug('toeIkchain: %s, %s' % (toeIkChain[0], type(toeIkChain[0])))
                logger.debug('toeIkCtrParents: %s' % (toeIkCtrParents))
                footMainJointsList[-1].addChild(toeMainChain[0])

            # ik foot ctr TODO: simplify this section
            # TODO: create the rest of the controllers here too
            footIkCtr = self.create_controller('%s_ik_%s_%s_foot_ctr' % (self.chName, zone, side), '%sIk_%s' % (zone, side), 1, 17)
            self.ctrGrp.addChild(footIkCtr)
            footIkControllerList.append(footIkCtr)  # append joint to list
            footIkAttrTypes = ['heel', 'tilt', 'toes', 'ball', 'footRoll']
            # add auto attributes
            for attr in footIkAttrTypes:
                pm.addAttr(footIkCtr, longName=attr, shortName=attr, type='float', defaultValue=0.0, k=True)

            pm.addAttr(footIkCtr, longName='showControls', shortName='showControls', type='bool', defaultValue=True, k=False)
            pm.setAttr('%s.showControls' % str(footIkCtr), channelBox=True)

            footRollCtr=[]  # list of footRoll ctr

            footIkCtrTypes = ('footHeel', 'footTiltIn', 'footTiltOut', 'footToes', 'footBall')
            for ctrType in footIkCtrTypes:
                footIkCtrWalk = self.create_controller('%s_ik_%s_%s_%s_ctr' % (self.chName, zone, side, ctrType), '%sIk_%s' % (ctrType, side), 1, 17)
                footIkControllerList[-1].addChild(footIkCtrWalk)
                footIkCtr.attr('showControls').connect(footIkCtrWalk.getShape().visibility)

                if 'tilt' not in ctrType.lower():
                    footRollCtr.append(footIkCtrWalk)  # save footRoll controllers
                if ctrType == 'footToes':
                    footToesIkCtr = footIkCtrWalk
                elif ctrType == 'footBall':
                    footBallIkCtr = footIkCtrWalk

                footIkControllerList.append(footIkCtrWalk)

            # once all are created, translate if necessary
            pm.xform(footIkCtr, ws=True, m=firstfootFkMatrix)
            footBallIkMatrix = [firstfootFkMatrix[0],firstfootFkMatrix[1],firstfootFkMatrix[2],firstfootFkMatrix[3],
                                                firstfootFkMatrix[4],firstfootFkMatrix[5],firstfootFkMatrix[6],firstfootFkMatrix[7],
                                                firstfootFkMatrix[8],firstfootFkMatrix[9],firstfootFkMatrix[10],firstfootFkMatrix[11],
                                                middleToeCtrMatrix[12], middleToeCtrMatrix[13], middleToeCtrMatrix[14], middleToeCtrMatrix[15]]
            pm.xform(footBallIkCtr, ws=True, m=footBallIkMatrix)

            for i in legIkControl.listRelatives(c=True, type='transform'):  # traspase childs from previous leg controller
                footBallIkCtr.addChild(i)

            #footBallIkCtr.addChild(ikHandle)  # add ik handle too
            # parent toes Ik ctr to footToes
            logger.debug('footToesIkCtr: %s, %s' % (footToesIkCtr, type(footToesIkCtr)))
            logger.debug('toeIkCtrParents: %s' % toeIkCtrParents)
            for toeCtr in toeIkCtrParents:
                footToesIkCtr.addChild(toeCtr)

            pm.delete(legIkControl.firstParent())  # if foot, we do not need this controller
            legIkControllerList.remove(legIkControl)

            # toes general Controller ik Fk review: no side review: ik ctrllers  simplyfy with for
            toesFkGeneralController = self.create_controller('%s_fk_%s_%s_toesGeneral_ctr' % (self.chName, zone, side), 'toesFk', 1, fkColor)
            pm.xform(toesFkGeneralController, ws=True, m=middleToeCtrMatrix)  # align to middle individual toe review
            toesIkGeneralController = self.create_controller('%s_ik_%s_%s_toesGeneral_ctr' % (self.chName, zone, side), 'toesFk', 1, fkColor)
            pm.xform(toesIkGeneralController, ws=True, m=middleToeCtrMatrix)
            # parent and store to lists
            footFkControllerList[-1].addChild(toesFkGeneralController)
            footToesIkCtr.addChild(toesIkGeneralController)
            toesFkControllerList.append(toesFkGeneralController)
            toesIkControllerList.append(toesIkGeneralController)

            # fk Roots and autos
            footFkRoots = createRoots(footFkControllerList)
            footFkAuto = createRoots(footFkControllerList, 'auto')
            footIkRoots = createRoots(footIkControllerList)
            footRollAuto = createRoots(footRollCtr, 'footRollAuto')
            footIkAuto = createRoots(footIkControllerList, 'auto')
            toesFkRoots = createRoots(toesFkControllerList)
            toesFkAuto = createRoots(toesFkControllerList, 'auto')
            toesIkRoots = createRoots(toesIkControllerList)
            toesIkAuto = createRoots(toesIkControllerList, 'auto')

            # connect toes rotate attributes
            for ikOrFk in [toesFkAuto, toesIkAuto]:
                toesGeneralCtrIkOrFk = toesFkGeneralController if ikOrFk == toesFkAuto else toesIkGeneralController
                logger.debug('toesGeneralCtrIkOrFk: %s, %s' % (toesGeneralCtrIkOrFk, type(toesGeneralCtrIkOrFk)))
                for iAuto in ikOrFk:
                    if 'toe' in str(iAuto) and 'toesGeneral' not in str(iAuto):
                        for axis in ('X', 'Y', 'Z'):
                            toesGeneralCtrIkOrFk.attr('rotate%s' % axis).connect(iAuto.attr('rotate%s' % axis))

            # ik ctr autos
            for i, autoGrp in enumerate(footIkAuto[1:]):
                footIkControllerList[0].attr(footIkAttrTypes[i]).connect(autoGrp.rotateZ)
                if 'footTiltIn' in str(autoGrp):
                    autoGrp.attr('minRotZLimitEnable').set(True)
                    autoGrp.attr('minRotZLimit').set(0)
                    footIkAttrTypes.insert(i, footIkAttrTypes[i])  # we have two tilt elements, so we add again the attr

                elif 'footTiltOut' in str(autoGrp):
                    autoGrp.attr('maxRotZLimitEnable').set(True)
                    autoGrp.attr('maxRotZLimit').set(0)

            # footRollAuto
            for autoGrp in footRollAuto:
                logger.debug('footRoolAutoGrp: %s, %s' % (autoGrp, type(autoGrp)))
                animNode = pm.createNode('animCurveTU', name='%s_animNode' % autoGrp)
                footIkControllerList[0].attr(footIkAttrTypes[-1]).connect(animNode.input)
                animNode.output.connect(autoGrp.rotateZ)

                if 'heel' in str(autoGrp).lower():
                    animNode.addKeyframe(-50, 50)
                    animNode.addKeyframe(0, 0)
                    animNode.addKeyframe(50, 0)
                    keyFrames = range(animNode.numKeys())
                    animNode.setTangentTypes(keyFrames, inTangentType='linear', outTangentType='linear')
                    animNode.setTangentTypes([keyFrames[0],keyFrames[-1]], inTangentType='clamped', outTangentType='clamped')
                    animNode.setPostInfinityType('linear')
                    animNode.setPreInfinityType('linear')

                elif 'toes' in str(autoGrp).lower():
                    animNode.addKeyframe(0, 0)
                    animNode.addKeyframe(50, 0)
                    animNode.addKeyframe(100, -90)
                    keyFrames = range(animNode.numKeys())
                    animNode.setTangentTypes(keyFrames, inTangentType='linear', outTangentType='linear')
                    animNode.setTangentTypes([keyFrames[0], keyFrames[-1]], inTangentType='clamped',
                                             outTangentType='clamped')
                    animNode.setPostInfinityType('linear')
                    animNode.setPreInfinityType('linear')

                elif 'ball' in str(autoGrp).lower():
                    animNode.addKeyframe(-50, 0)
                    animNode.addKeyframe(0, 0)
                    animNode.addKeyframe(50, -60)
                    animNode.addKeyframe(100, 40)
                    keyFrames = range(animNode.numKeys())
                    animNode.setTangentTypes(keyFrames, inTangentType='linear', outTangentType='linear')
                    animNode.setTangentTypes([keyFrames[0], keyFrames[-1]], inTangentType='clamped',
                                             outTangentType='clamped')
                    animNode.setPostInfinityType('linear')
                    animNode.setPreInfinityType('linear')

            # orient constraint main to ik or fk foot
            for i, mainJoint in enumerate(footMainJointsList):
                if i == 0:
                    orientConstraint = pm.orientConstraint(footIkControllerList[-1], footFkControllerList[i], mainJoint, maintainOffset=True, name='%s_main_blending_orientConstraint' % str(mainJoint))
                    ikFkshape.ikFk.connect(orientConstraint.attr('%sW0' % str(footIkControllerList[-1])))  # shape with bleeding attribute
                    ikFkshape.ikFk.connect(footIkControllerList[i].visibility)  # all foot chain visibility

                    # parent shape and clone Shape
                    footIkControllerList[-1].addChild(ikFkshape, s=True, add=True)

                    # parent shape
                    footFkControllerList[i].addChild(ikFkshape, s=True, add=True)

                    plusMinusIkFk.output1D.connect(orientConstraint.attr('%sW1' % str(footFkControllerList[i])))
                    plusMinusIkFk.output1D.connect(footFkControllerList[i].getShape().visibility)

                else:
                    orientConstraint = pm.orientConstraint(footFkControllerList[i], mainJoint, maintainOffset=True, name='%s_orientConstraint' % str(mainJoint))


                lockAndHideAttr(footFkControllerList[i], True, False, False)
                pm.setAttr('%s.radi' % footFkControllerList[i], channelBox=False, keyable=False)

                # connect to deform skeleton fixme: no tips in main // orient constraint names // toes names and foot names
                orientDeformConstraint = pm.orientConstraint(mainJoint, footJoints[i], maintainOffset=False, name='%s_orientConstraint' % str(footJoints[i]))

            # main ik fk toes
            for i, mainJoint in enumerate(toesMainJointsList):
                orientConstraint = pm.orientConstraint(toesIkControllerList[i], toesFkControllerList[i], mainJoint, maintainOffset=True,
                                                       name='%s_orientConstraint' % str(mainJoint))

                pointConstraint = pm.pointConstraint(toesIkControllerList[i], toesFkControllerList[i], mainJoint, maintainOffset=False,
                                                       name='%s_pointConstraint' % str(mainJoint))

                ikFkshape.ikFk.connect(orientConstraint.attr('%sW0' % str(toesIkControllerList[i])))  # shape with bleeding attribute
                ikFkshape.ikFk.connect(pointConstraint.attr('%sW0' % str(toesIkControllerList[i])))  # shape with bleeding attribute
                ikFkshape.ikFk.connect(toesIkControllerList[i].visibility)  # all foot chain visibility

                # parent shape and clone Shape
                footIkControllerList[i].addChild(ikFkshape, s=True, add=True)

                # parent shape fk
                toesFkControllerList[i].addChild(ikFkshape, s=True, add=True)

                plusMinusIkFk.output1D.connect(orientConstraint.attr('%sW1' % str(toesFkControllerList[i])))
                plusMinusIkFk.output1D.connect(pointConstraint.attr('%sW1' % str(toesFkControllerList[i])))
                plusMinusIkFk.output1D.connect(toesFkControllerList[i].visibility)

                lockAndHideAttr(toesFkControllerList[i], True, False, False)
                pm.setAttr('%s.radi' % toesFkControllerList[i], channelBox=False, keyable=False)

                # connect to deform skeleton
                orientDeformConstraint = pm.orientConstraint(mainJoint, toesJoints[i], maintainOffset=False, name='%s_orientConstraint' % str(toesJoints[i]))
                pointDeformConstraint = pm.pointConstraint(mainJoint, toesJoints[i], maintainOffset=False, name='%s_pointConstraint' % str(toesJoints[i]))

            return footIkControllerList + toesIkControllerList, footFkControllerList + toesFkControllerList

        if footAuto:
            footIkCtrList, footFkCtrList = foot_auto(side)
            legIkControllerList = legIkControllerList + footIkCtrList
            legFkControllersList = legFkControllersList + footFkCtrList
        else:
            # parent shape
            legIkControl.addChild(ikFkshape, r=True, s=True)
        pm.delete(ikFkNode)

        # save Data
        # todo: save quaternions too if necessary
        zoneSide = '%s_%s' % (zone, side)
        self.joints[zoneSide] = legJoints
        self.ikControllers[zoneSide] = legIkControllerList
        self.fkControllers[zoneSide] = legFkControllersList
        self.ikHandles[zoneSide] = ikHandle

        return legIkControllerList, legFkControllersList


    @checker_auto('decorated')
    def arm_auto(self, side, zone='arm'):
        """
        # TODO: zone out of args?
        # TODO: organize and optimize this method
        auto build a ik fk arm
        Args:
            side: left or right
            zone: arm
        """
        fkColor = 14 if side == 'left' else 29
        armJoints = [point for point in pm.ls() if re.match('^%s.*([aA]rm).*%s.*joint$' % (self.chName, side), str(point))]
        clavicleJoints = [point for point in pm.ls() if re.match('^%s.*(clavicle).*%s.*joint$' % (self.chName, side), str(point))]
        logger.debug('%s joints: %s' % (side, armJoints))

        # fk controllers are copies of arm joints
        # save controllers name
        armFkControllersList = []
        clavicleControllerList = []
        armIkControllerList = []
        armMainJointList = []
        armIkJointList = []

        NameIdList = []  # store idNames. p.e upperLeg, lowerLeg

        # duplicate joints
        # todo: conenct clavicle deform
        for joint in armJoints:
            controllerName = str(joint).split('_')[1]
            armFkControllersList.append(joint.duplicate(po=True, name='%s_fk_%s_%s_%s_ctr' % (self.chName, zone, side, controllerName))[0])
            armIkJointList.append(joint.duplicate(po=True, name='%s_ik_joint_%s_%s_%s_joint' % (self.chName, zone, side, controllerName))[0])
            armMainJointList.append(joint.duplicate(po=True, name='%s_main_joint_%s_%s_%s_joint' % (self.chName, zone, side, controllerName))[0])

            NameIdList.append(controllerName)

        # duplicate clavicle
        for joint in clavicleJoints:
            controllerName = str(joint).split('_')[1]
            clavicleControllerList.append(joint.duplicate(po=True, name='%s_fk_%s_%s_%s_ctr' % (self.chName, zone, side, controllerName))[0])
            NameIdList.append(controllerName)

        # reconstruct hierarchy
        # create Fk control shapes
        for i, fkCtr in enumerate(armFkControllersList[:-1]):  # last controller does not has shape
            # ik hierarchy
            armIkJointList[i].addChild(armIkJointList[i + 1])
            # main hierarchy
            armMainJointList[i].addChild(armMainJointList[i+1])

            fkCtr.addChild(armFkControllersList[i+1])
            # fk controls
            shapeFkTransform = self.create_controller('%sShape' % str(fkCtr), '%sFk_%s' % (NameIdList[i], side),1, fkColor)
            # parentShape
            fkCtr.addChild(shapeFkTransform.getShape(), s=True, r=True)
            # delete shape transform
            pm.delete(shapeFkTransform)

        # ik control
        armIkControl = self.create_controller('%s_ik_%s_%s_ctr' % (self.chName, zone, side), '%sIk_%s' % (zone, side), 1, 17)
        pm.xform(armIkControl, ws=True, m=pm.xform(armJoints[-1], q=True, ws=True, m=True))
        #legIkControl.setTranslation(armJoints[-1].getTranslation('world'), 'world')
        self.ctrGrp.addChild(armIkControl)  # parent to ctr group

        # clavicle fk control
        for i, fkCtr in enumerate(clavicleControllerList):  # last controller does not has shape
            # fk controls
            shapeFkTransform = self.create_controller('%sShape' % str(fkCtr), '%sFk_%s' % (NameIdList[-1], side),1, fkColor)
            # parentShape
            fkCtr.addChild(shapeFkTransform.getShape(), s=True, r=True)
            # delete shape transform
            pm.delete(shapeFkTransform)

        # organitze outliner
        self.ikControllers['spine'][-1].addChild(clavicleControllerList[0])
        clavicleControllerList[-1].addChild(armFkControllersList[0])
        clavicleControllerList[-1].addChild(armMainJointList[0])
        clavicleControllerList[-1].addChild(armIkJointList[0])

        # save to list
        armIkControllerList.append(armIkControl)
        createRoots(armIkControllerList)

        # fkRoots
        createRoots(armFkControllersList)
        createRoots(armFkControllersList, 'auto')

        # set preferred angle
        armIkJointList[1].preferredAngleZ.set(-15)
        # ik solver, clavicle out of ik control
        ikHandle, ikEffector = pm.ikHandle(startJoint=armIkJointList[0], endEffector=armIkJointList[-1], solver='ikRPsolver', name='%s_ik_%s_%s_handle' % (self.chName, zone, side))
        ikEffector.rename('%s_ik_%s_%s_effector' % (self.chName, zone, side))
        armIkControl.addChild(ikHandle)
        # create poles
        armPoleController = self.create_controller('%s_ik_%s_%s_pole_ctr' % (self.chName, zone, side), 'pole')
        relocatePole(armPoleController, armIkJointList, 35)  # relocate pole Vector
        self.ikControllers['spine'][-1].addChild(armPoleController)
        # constraint poleVector
        pm.poleVectorConstraint(armPoleController, ikHandle)

        # root poleVector
        createRoots([armPoleController])

        # main blending
        # unknown node to store blend info
        # locator shape instanced version
        ikFkNode = pm.spaceLocator(name='%s_%s_%s_attr' % (self.chName, zone, side))
        ikFkshape = ikFkNode.getShape()
        pm.addAttr(ikFkshape, longName='ikFk', shortName='ikFk', minValue=0.0, maxValue=1.0, type='float', defaultValue=0.0, k=True)
        # hide unused attributes
        for attr in ('localPosition', 'localScale'):
            for axis in ('X', 'Y', 'Z'):
                pm.setAttr('%s.%s%s' % (ikFkshape, attr, axis), channelBox=False, keyable=False)

        plusMinusIkFk = pm.createNode('plusMinusAverage', name='%s_ikFk_blending_%s_%s_plusMinusAverage' % (self.chName, zone, side))
        ikFkNode.ikFk.connect(plusMinusIkFk.input1D[1])
        plusMinusIkFk.input1D[0].set(1)
        plusMinusIkFk.operation.set(2)

        # iterate along main joints
        # todo: visibility
        for i, joint in enumerate(armMainJointList):
            # attributes  fk +1 because clavicle
            orientConstraint = pm.orientConstraint(armIkJointList[i], armFkControllersList[i], joint, maintainOffset=False, name='%s_main_blending_%s_%s_orientConstraint' % (self.chName, zone, side))
            ikFkNode.ikFk.connect(orientConstraint.attr('%sW0' % str(armIkJointList[i])))
            ikFkNode.ikFk.connect(armIkJointList[i].visibility)

            # clone instanced
            ikfkNodeInstance = ikFkNode.duplicate(instanceLeaf=True)[0]
            # parent shape
            armFkControllersList[i].addChild(ikfkNodeInstance.getShape(), r=True, s=True)
            pm.delete(ikfkNodeInstance)

            plusMinusIkFk.output1D.connect(orientConstraint.attr('%sW1' % str(armFkControllersList[i])))
            plusMinusIkFk.output1D.connect(armFkControllersList[i].visibility)

            lockAndHideAttr(armFkControllersList[i], True, False, False)
            pm.setAttr('%s.radi' % armFkControllersList[i], channelBox=False, keyable=False)

            # connect to deform skeleton
            armParentConstraint = pm.orientConstraint(joint, armJoints[i], maintainOffset=False, name='%s_main_%s_%s_parentConstraint' % (self.chName, zone, side))

        # clavicle contraint
        clavicleOrientConstraint = pm.orientConstraint(clavicleControllerList[0], clavicleJoints[0], maintainOffset=False, name='%s_main_%s_%s_parentConstraint' % (self.chName, zone, side))
        claviclePointConstraint = pm.pointConstraint(clavicleControllerList[0], clavicleJoints[0], maintainOffset=False, name='%s_main_%s_%s_parentConstraint' % (self.chName, zone, side))

        # ik blending controller attr
        ikFkshape.ikFk.connect(armPoleController.visibility)
        ikFkshape.ikFk.connect(armIkControl.visibility)
        # parent shape
        armIkControl.addChild(ikFkshape, r=True, s=True)
        pm.delete(ikFkNode)

        # twist Bone

        # save Data
        zoneSide = '%s_%s' % (zone, side)
        self.joints[zoneSide] = armJoints
        self.ikControllers[zoneSide] = armIkControllerList
        totalArmFkList = armFkControllersList + clavicleControllerList  # add clavicle to arm fk controllers
        self.fkControllers[zoneSide] = totalArmFkList

        return armIkControllerList, totalArmFkList

    def create_controller(self, name, controllerType, s=1.0, colorIndex=4):
        """
        Args:
            name: name of controller
            controllerType(str): from json controller types
        return:
            controller: pymel transformNode
            transformMatrix: stored position
        """
        controller, transformMatrix = ctrSaveLoadToJson.ctrLoadJson(controllerType, self.chName, self.path, s, colorIndex)
        controller = pm.PyNode(controller)
        controller.rename(name)

        shapes = controller.listRelatives(s=True)
        # hide shape attr
        for shape in shapes:
            for attr in ('aiRenderCurve', 'aiCurveWidth', 'aiSampleRate', 'aiCurveShaderR', 'aiCurveShaderG', 'aiCurveShaderB'):
                pm.setAttr('%s.%s' % (str(shape), attr), channelBox=False, keyable=False)

        pm.xform(controller, ws=True, m=transformMatrix)
        logger.debug('controller %s' % controller)
        return controller

#######
#utils#
#######
def relocatePole(pole, joints, distance=1):
    """
    relocate pole position for pole vector
    at the moment, valid for 3 joints.
    not calculate rotation
    TODO: calculate rotation. matrix transform
    Args:
        pole: PyNode of pole
        joints: list of joints, pm nodes
    """
    # first vector
    position1 = joints[0].getTranslation('world')
    position2 = joints[1].getTranslation('world')
    vector1 = OpenMaya.MVector(position2[0]-position1[0],position2[1]-position1[1],position2[2]-position1[2])
    vector1.normalize()

   # second vector
    position1 = joints[-1].getTranslation('world')
    position2 = joints[-2].getTranslation('world')
    vector2 = OpenMaya.MVector(position2[0]-position1[0],position2[1]-position1[1],position2[2]-position1[2])
    vector2.normalize()

    # z vector
    poleVector = (vector1 + vector2)
    poleVector.normalize()

    # x vector cross product
    xVector = vector2 ^ poleVector
    xVector.normalize()

    # y vector cross product
    yVector = poleVector ^ xVector
    yVector.normalize()

    pole.setTransformation([xVector.x, xVector.y, xVector.z, 0, yVector.x, yVector.y, yVector.z, 0, poleVector.x, poleVector.y, poleVector.z, 0,
                       poleVector.x * distance + position2[0], poleVector.y * distance + position2[1], poleVector.z * distance + position2[2],
                      1])

def createRoots(list, sufix='root'):
    roots = []
    for arg in list:
        try:
            parent = arg.firstParent()
        except:
            parent = None
        # explanation: pm getTransformation gives transform matrix in object space.
        # so we need to use pm.xform()
        rootGrp = pm.group(em=True, name='%s_%s' % (arg, sufix))
        matrixTransform = pm.xform(arg, q=True, ws=True, m=True)
        pm.xform(rootGrp, ws=True, m=matrixTransform)

        if parent:
            parent.addChild(rootGrp)
        rootGrp.addChild(arg)

        # if is a joint, assegure reset values
        if isinstance(arg, pm.nodetypes.Joint):
            for axis in ('X', 'Y', 'Z'):
                arg.attr('jointOrient%s' % axis).set(0.0)

            arg.setRotation((0,0,0), 'object')

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