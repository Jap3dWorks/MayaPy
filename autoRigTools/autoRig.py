import pymel.core as pm
import re
from maya import OpenMaya
from autoRigTools import ctrSaveLoadToJson
from autoRigTools import ARCore
reload(ARCore)
reload(ctrSaveLoadToJson)  # review: reload

import inspect

import logging
logging.basicConfig()
logger = logging.getLogger('autoRig:')
logger.setLevel(logging.DEBUG)

# TODO: main Joints, naming pe. akona_foreArm_main. similar a joint name
# TODO: Name convention revision
# name convention:
# name_ctrName_zone_side_function_type:
# akona_chest_spine_IK_ctr
# akona_foreArm_arm_left_twist1_jnt

class RigAuto(object):

    def __init__(self, chName, path):
        """
        autoRig class tools
        """
        # TODO: create node Module or chName_rig_grp transform node with messages attributes to store connections
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

        # create Main ctr
        try:
            self.mainCtr = pm.PyNode('%s_main_grp' % self.chName)
            self.ctrGrp.addChild(self.mainCtr)
        except:
            self.mainCtr = self.create_controller('%s_main_grp' % self.chName, 'main', 1, 18)
            self.ctrGrp.addChild(self.mainCtr)
        # connect main scale to grp joints
        ARCore.connectAttributes(self.mainCtr, pm.PyNode('%s_joints_grp' % self.chName), ['scale'], ['X', 'Y', 'Z'])

        # I think i don't need this
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
    #@checker_auto('decorated')
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
        ARCore.snapCurveToPoints(spineJoints, spineCurve, 16, 0.01)

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
                ARCore.lockAndHideAttr(spineController, False, True, True)

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
                self.mainCtr.addChild(spineFKControllerList[0])

        # create roots grp
        ARCore.createRoots(spineFKControllerList)
        spineControllerRootsList = ARCore.createRoots(spineIKControllerList)

        # once created roots, we can freeze and hide attributes. if not, it can be unstable
        for neckHeadIKCtr in spineFKControllerList[1:]:
            ARCore.lockAndHideAttr(neckHeadIKCtr, True, False, False)

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

        for n, joint in enumerate(spineJoints):
            # for each joint, create a multiply divide node
            # formula for scale: 1+(factorScale - 1)*influence
            # TODO: rename all this

            jointNameSplit = str(joint).split('_')[1]  # review, maybe better store joints name in a list

            # TODO: do this more legible if it is possible
            if re.match('.*(end|hips).*', str(joint)):
                # last joint and first joint connect to controller
                # if hips, use de min val, zero. when end, n will be bigger than ik controllers, so use  the last ik controller.
                spineIkCtrConstr = spineIKControllerList[min(n, len(spineIKControllerList)-1)]
                spineIkCtrConstr.rename(str(joint).replace('joint', 'ctr'))  # rename ctr, useful for snap proxy model
                # constraint
                pm.pointConstraint(jointDriverList[n], joint, maintainOffset=False,  name='%s_drv_%s_%s_1_pointConstraint' % (self.chName, zone, jointNameSplit))
                endJointOrientConstraint = pm.orientConstraint(spineIKControllerList[min(n, len(spineIKControllerList)-1)], joint, maintainOffset=True, name='%s_drv_%s_%s_1_orientConstraint' % (self.chName, zone, jointNameSplit))
                endJointOrientConstraint.interpType.set(0)

            else:
                # connect to deform joints
                jointDriverList[n].rename(str(joint).replace('joint', 'main'))  # rename driver, useful for snap proxy model
                pm.parentConstraint(jointDriverList[n], joint, maintainOffset=True, name='%s_drv_%s_%s_1_parentConstraint' % (self.chName, zone, jointNameSplit))

        # stretch TODO: print spineJoints list
        ARCore.stretchCurveVolume(spineCurve, spineJoints, '%s_%s' % (self.chName, zone), self.mainCtr)

        # save data
        self.joints[zone] = spineJoints
        self.ikControllers[zone] = spineIKControllerList
        self.fkControllers[zone] = spineFKControllerList
        return spineIKControllerList, spineFKControllerList

    #@checker_auto('decorated')
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
        ARCore.snapCurveToPoints(neckHeadJoints[:-1], neckHeadCurve, 16, 0.01)

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
        neckHeadFKCtrRoots = ARCore.createRoots(neckHeadFKCtrList)
        neckHeadIKCtrRoots = ARCore.createRoots(neckHeadIKCtrList)
        # once created roots, we can freeze and hide attributes. if not, it can be unstable
        for neckHeadFKCtr in neckHeadFKCtrList:
            ARCore.lockAndHideAttr(neckHeadFKCtr, True, False, False)
        # lock and hide neck attr, it's here because we have only one
        ARCore.lockAndHideAttr(neckHeadIKCtrList[0], False, True, True)

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
        self.mainCtr.addChild(baseOrientAuto)

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
                # orient to controller
                neckHeadIKCtrList[-1].rename(str(joint).replace('joint', 'ctr'))  # rename, useful for snap proxy model
                pm.orientConstraint(neckHeadIKCtrList[-1], joint, maintainOffset=True, name='%s_drv_%s_%s_1_orientConstraint' % (self.chName, zone, jointNameSplit))

            else:
                jointDriverList[n].rename(str(joint).replace('joint', 'main'))  # rename, useful for snap proxy model
                pm.parentConstraint(jointDriverList[n], joint, maintainOffset=True, name='%s_drv_%s_%s_1_parentConstraint' % (self.chName, zone, jointNameSplit))

        # stretch
        ARCore.stretchCurveVolume(neckHeadCurve, neckHeadJoints[:-1], '%s_%s' % (self.chName, zone), self.mainCtr)

        # save data
        self.joints[zone] = neckHeadJoints
        self.ikControllers[zone] = neckHeadIKCtrList
        self.fkControllers[zone] = neckHeadFKCtrList
        return neckHeadIKCtrList, neckHeadFKCtrList

    #TODO: rename method ikFkChain_auto
    #@checker_auto('decorated')
    def ikFkChain_auto(self, side, parent, zone='leg', stretch=True, *funcs):
        """
        # TODO: organize and optimize this method
        auto build a ik fk leg
        Args:
            side: left or right
            zone: leg or arm
            stretch(bool): if true, create stretch system or hand
            restPoints(list):  with rest points
        """
        zoneA = zone
        self.lastZone = zone  # review
        fkColor = 14 if side == 'left' else 29
        pointColor = 7 if side == 'left' else 5
        # be careful with poseInterpolator
        legJoints = [point for point in pm.ls() if re.match('^%s.*(%s).(?!twist).*%s.*joint$' % (self.chName, zoneA, side), str(point).lower())]
        self.legTwistJoints = [point for point in pm.ls() if re.match('^%s.*(%s).(twist).*%s.*joint$' % (self.chName, zoneA, side), str(point).lower())]
        logger.debug('%s %s joints: %s' % (side, zoneA, legJoints))
        logger.debug('%s %s twist joints: %s' % (side, zoneA, self.legTwistJoints))

        # group for leg controls
        self.legCtrGrp = pm.group(empty=True, name='%s_ik_%s_%s_ctrGrp_root' % (self.chName, zoneA, side))
        self.mainCtr.addChild(self.legCtrGrp)

        # sync legTwistJoints index with leg joints index
        legTwistSyncJoints = ARCore.syncListsByKeyword(legJoints, self.legTwistJoints, 'twist')

        # fk controllers are copies of leg joints
        # save controllers name
        self.legFkControllersList = []
        self.legIkControllerList = []
        self.legMainJointList = []
        legTwistList = []
        self.legIkJointList = []

        NameIdList = []  # store idNames. p.e upperLeg, lowerLeg

        # duplicate joints
        for n, i in enumerate(legJoints):
            controllerName = str(i).split('_')[1] if 'end' not in str(i) else 'end'  # if is an end joint, rename end
            self.legFkControllersList.append(i.duplicate(po=True, name='%s_fk_%s_%s_%s_ctr' % (self.chName, zoneA, side, controllerName))[0])
            self.legIkJointList.append(i.duplicate(po=True, name='%s_ik_%s_%s_%s_joint' % (self.chName, zoneA, side, controllerName))[0])
            self.legMainJointList.append(i.duplicate(po=True, name='%s_main_%s_%s_%s_joint' % (self.chName, zoneA, side, controllerName))[0])

            ### twist Joints ####
            if legTwistSyncJoints[n]:
                legTwistIni = [i.duplicate(po=True, name='%s_twist0_%s_%s_%s_joint' % (self.chName, zoneA, side, controllerName))[0]]

                for j, twstJnt in enumerate(legTwistSyncJoints[n]):
                    # duplicate and construc hierarchy
                    legTwistIni.append(twstJnt.duplicate(po=True, name='%s_twist%s_%s_%s_%s_joint' % (self.chName, j+1, zoneA, side, controllerName))[0])
                    legTwistIni[-2].addChild(legTwistIni[-1])

                legTwistList.append(legTwistIni)  # append to list of tJoints
                self.mainCtr.addChild(legTwistIni[0])

                # parent twist joints
                if n == 0:
                    parent.addChild(legTwistIni[0])  # first to ctr ik hips
                else:
                    self.legMainJointList[-2].addChild(legTwistIni[0])  # lower twist child of upper leg

                # create twist group orient tracker, if is chaint before foot or hand, track foot or hand
                if legTwistSyncJoints[n] == legTwistSyncJoints[-2]:  # just before end joint
                    self.footTwstList = list(legTwistIni)
                    self.footTwstZone = zoneA
                    self.footTwstCtrName = controllerName
                    self.footpointCnstr = self.legMainJointList[-1]

                else:
                    # connect and setup leg Twist Ini chain
                    ARCore.twistJointsConnect(legTwistIni, self.legMainJointList[-1], '%s_%s_%s_%s' % (self.chName, controllerName, zoneA, side))

            NameIdList.append(controllerName)

        logger.debug('leg IK joints: %s' % self.legIkJointList)

        # reconstruct hierarchy
        # create Fk control shapes
        for i, fkCtr in enumerate(self.legFkControllersList[:-1]):  # last controller does not has shape
            # ik hierarchy
            self.legIkJointList[i].addChild(self.legIkJointList[i + 1])
            # main hierarchy
            self.legMainJointList[i].addChild(self.legMainJointList[i+1])

            fkCtr.addChild(self.legFkControllersList[i+1])
            # fk controls
            shapeFkTransform = self.create_controller('%sShape' % str(fkCtr), '%sFk_%s' % (NameIdList[i], side), 1, fkColor)
            # parentShape
            fkCtr.addChild(shapeFkTransform.getShape(), s=True, r=True)
            # delete shape transform
            pm.delete(shapeFkTransform)

        # ik control
        self.legIkControl = self.create_controller('%s_ik_%s_%s_ctr' % (self.chName, zoneA, side), '%sIk_%s' % (zoneA, side), 1, 17)
        # pm.xform(legIkControl, ws=True, m=pm.xform(legJoints[-1], q=True, ws=True, m=True))
        self.legIkControl.setTranslation(legJoints[-1].getTranslation('world'), 'world')
        self.legCtrGrp.addChild(self.legIkControl)  # parent to ctr group

        # organitze outliner
        parent.addChild(self.legFkControllersList[0])
        parent.addChild(self.legMainJointList[0])
        parent.addChild(self.legIkJointList[0])

        # save to list
        self.legIkControllerList.append(self.legIkControl)
        ARCore.createRoots(self.legIkControllerList)

        # fkRoots
        self.legFkCtrRoots = ARCore.createRoots(self.legFkControllersList)
        ARCore.createRoots(self.legFkControllersList, 'auto')

        # set preferred angle
        self.legIkJointList[1].preferredAngleZ.set(-15)
        # ik solver
        ikHandle, ikEffector = pm.ikHandle(startJoint=self.legIkJointList[0], endEffector=self.legIkJointList[-1], solver='ikRPsolver', name='%s_ik_%s_%s_handle' % (self.chName, zoneA, side))
        ikEffector.rename('%s_ik_%s_%s_effector' % (self.chName, zoneA, side))
        self.legIkControl.addChild(ikHandle)
        # create poles
        legPoleController = self.create_controller('%s_ik_%s_%s_pole_ctr' % (self.chName, zoneA, side), 'pole',2)
        ARCore.relocatePole(legPoleController, self.legIkJointList, 35)  # relocate pole Vector
        self.legCtrGrp.addChild(legPoleController)
        pm.addAttr(legPoleController, ln='polePosition', at='enum', en="world:root:foot", k=True)
        # save poleVector
        self.legIkControllerList.append(legPoleController)

        # constraint poleVector
        pm.poleVectorConstraint(legPoleController, ikHandle)

        # root poleVector
        legPoleVectorAuto = ARCore.createRoots([legPoleController])
        ARCore.createRoots([legPoleController])

        # TODO: abstract more
        # poleVectorAttributes
        poleAttrgrp=[]
        legPoleAnimNodes=[]
        for attr in ('world', 'root', zoneA):
            legPoleGrp = pm.group(empty=True, name= '%s_ik_%s_%s_pole%s_grp' % (self.chName, zoneA, attr.capitalize(), side))
            poleAttrgrp.append(legPoleGrp)
            pm.xform(legPoleGrp, ws=True, m=pm.xform(legPoleVectorAuto, ws=True, m=True, q=True))
            legPoleAnim = pm.createNode('animCurveTU', name='%s_ik_%s_%s_pole%s_animNode' % (self.chName, zoneA, attr.capitalize(), side))
            legPoleController.attr('polePosition').connect(legPoleAnim.input)
            legPoleAnimNodes.append(legPoleAnim)

            if attr == 'world':
                legPoleAnim.addKeyframe(0, 1)
                legPoleAnim.addKeyframe(1, 0)
                legPoleAnim.addKeyframe(2, 0)
                self.legCtrGrp.addChild(legPoleGrp)
            elif attr == 'root':
                legPoleAnim.addKeyframe(0, 0)
                legPoleAnim.addKeyframe(1, 1)
                legPoleAnim.addKeyframe(2, 0)
                parent.addChild(legPoleGrp)
            elif attr == zoneA:
                legPoleAnim.addKeyframe(0, 0)
                legPoleAnim.addKeyframe(1, 0)
                legPoleAnim.addKeyframe(2, 1)
                self.legIkControl.addChild(legPoleGrp)

        # once node are created, connect them
        polegrpsParentCnstr=pm.parentConstraint(poleAttrgrp[0],poleAttrgrp[1],poleAttrgrp[2], legPoleVectorAuto, maintainOffset=False, name='%s_pointConstraint' % legPoleVectorAuto)
        for i, poleAttr in enumerate(poleAttrgrp):
            legPoleAnimNodes[i].output.connect(polegrpsParentCnstr.attr('%sW%s' % (str(poleAttr), i)))


        # main blending
        # unknown node to store blend info
        # locator shape instanced version
        ikFkNode = pm.spaceLocator(name='%s_%s_%s_attr' % (self.chName, zoneA, side))
        self.ikFkshape = ikFkNode.getShape()
        self.ikFkshape.visibility.set(0)
        pm.addAttr(self.ikFkshape, longName='ikFk', shortName='ikFk', minValue=0.0, maxValue=1.0, type='float', defaultValue=1.0, k=True)
        # hide unused attributes
        for attr in ('localPosition', 'localScale'):
            for axis in ('X', 'Y', 'Z'):
                pm.setAttr('%s.%s%s' % (self.ikFkshape, attr, axis), channelBox=False, keyable=False)

        self.plusMinusIkFk = pm.createNode('plusMinusAverage', name='%s_ikFk_blending_%s_%s_plusMinusAverage' % (self.chName, zoneA, side))
        self.ikFkshape.ikFk.connect(self.plusMinusIkFk.input1D[1])
        self.plusMinusIkFk.input1D[0].set(1)
        self.plusMinusIkFk.operation.set(2)

        if stretch:
            ###Strech###
            # fk strech
            legFkrootsDistances, legMaxiumDistance = ARCore.calcDistances(self.legFkCtrRoots)  # review:  legIkJointList[0]   legIkCtrRoot
            #ikFkStretchSetup
            ARCore.stretchIkFkSetup(self.legFkCtrRoots[1:], legFkrootsDistances, self.ikFkshape, [self.legIkJointList[0], ikHandle],
                                    legMaxiumDistance, self.legIkJointList[1:], self.legMainJointList[1:], legTwistList, '%s_%s_%s' % (self.chName, zoneA, side), self.mainCtr, legPoleController)

        # iterate along main joints
        # blending
        # todo: visibility, connect to ikFkShape
        legPointControllers=[]
        for i, joint in enumerate(self.legMainJointList):
            # attributes
            orientConstraint = pm.orientConstraint(self.legIkJointList[i], self.legFkControllersList[i], joint, maintainOffset=False, name='%s_main_blending_%s_%s_orientConstraint' % (self.chName, zoneA, side))
            self.ikFkshape.ikFk.connect(orientConstraint.attr('%sW0' % str(self.legIkJointList[i])))
            self.ikFkshape.ikFk.connect(self.legIkJointList[i].visibility)

            # parent shape
            self.legFkControllersList[i].addChild(self.ikFkshape, s=True, add=True)

            self.plusMinusIkFk.output1D.connect(orientConstraint.attr('%sW1' % str(self.legFkControllersList[i])))
            # review: visibility shape
            self.plusMinusIkFk.output1D.connect(self.legFkControllersList[i].visibility)

            ARCore.lockAndHideAttr(self.legFkControllersList[i], True, False, False)
            pm.setAttr('%s.radi' % self.legFkControllersList[i], channelBox=False, keyable=False)

            # connect to deform skeleton review parent
            # conenct with twist joints
            aimPointList=[]
            if self.legTwistJoints:
                if len(legTwistList) > i:  # exclude last twist joint, empty items of a list
                    logger.debug('leg twist list: %s' % legTwistList)
                    for j, twistJnt in enumerate(legTwistList[i]):  # exclude first term review?
                        # leg joint or specific twist
                        skinJoint = legJoints[i] if j == 0 else legTwistSyncJoints[i][j-1]  # skined joints

                        nametype = 'main' if j == 0 else 'twist%s' % j
                        # orient and scale
                        #pm.orientConstraint(twistJnt, skinJoint, maintainOffset=False,name='%s_%s_%s_%s_%s_orientConstraint' % (self.chName, nametype, zoneA, side, NameIdList[i]))
                        aimGrp = pm.group(empty=True, name=str(skinJoint).replace('joint', 'main'))
                        pm.xform(aimGrp, ws=True, m=pm.xform(skinJoint, ws=True, q=True, m=True))

                        # connect orient to deform joints
                        pm.orientConstraint(aimGrp, skinJoint, maintainOffset=False)

                        twistJnt.scaleY.connect(skinJoint.scaleY)
                        twistJnt.scaleZ.connect(skinJoint.scaleZ)

                        aimPointList.append(aimGrp)

                        # points two first
                        if (i==0 and j==0):  # first joints
                            parent.addChild(aimGrp)

                        elif (i == len(legTwistList)-1 and j == len(legTwistList[i])-1):
                            # last joints
                            twistJnt.addChild(aimGrp)
                            pm.aimConstraint(aimGrp, aimPointList[-2], aimVector=(skinJoint.translateX.get(), 0, 0),
                                             worldUpType='objectrotation', worldUpObject=legPointControllers[-1])


                        elif i > 0 and j == 0:  # first joint not first twist chain
                            pointController = legPointControllers[-1]
                            pointController.addChild(aimGrp)

                        else:
                            pointController = self.create_controller('%s_%s_%s_%s_%s_ctr' % (self.chName, nametype, zoneA, side, NameIdList[i]), '%sTwistPoint_%s' % (zoneA, side), 1, pointColor)
                            pointController, rootPointController, pointConstraint = ARCore.jointPointToController([twistJnt], pointController)
                            joint.addChild(rootPointController[0])
                            pointController = pointController[0]
                            legPointControllers.append(pointController)  # save to list
                            pointController.addChild(aimGrp)
                            # aim constraint
                            if (j==1):  # second joint, worldup object parent ctr
                                pm.aimConstraint(aimGrp, aimPointList[-2], aimVector=(skinJoint.translateX.get(), 0, 0),
                                                 worldUpType='objectrotation', worldUpObject=legTwistList[i][0])
                            else:
                                pm.aimConstraint(aimGrp, aimPointList[-2], aimVector=(skinJoint.translateX.get(),0,0), worldUpType='objectrotation', worldUpObject=legPointControllers[-2])

                        pm.pointConstraint(aimGrp, skinJoint, maintainOffset=True, name='%s_%s_%s_%s_%s_pointConstraint' % (self.chName, nametype, zoneA, side, NameIdList[i]))


            else:
                # connect to deform skeleton
                joint.rename(str(legJoints[i]).replace('joint', 'main'))  # rename, useful for snap proxy model
                pm.orientConstraint(joint, legJoints[i], maintainOffset=False, name='%s_main_%s_%s_parentConstraint' % (self.chName, zoneA, side))
                pm.pointConstraint(joint, legJoints[i], maintainOffset=False, name='%s_main_%s_%s_parentConstraint' % (self.chName, zoneA, side))

        # ik blending controller attr
        self.ikFkshape.ikFk.connect(legPoleController.visibility)
        self.ikFkshape.ikFk.connect(self.legIkControl.visibility)
        self.legIkControl.addChild(self.ikFkshape, add=True, s=True)

        # function for create foots, Review: maybe here another to create hands
        for func in funcs:
            ikControllers, fkControllers = func()
            self.legIkControllerList = self.legIkControllerList + ikControllers
            self.legFkControllersList = self.legFkControllersList + fkControllers

        # save Data
        # todo: save quaternions too if necessary
        zoneSide = '%s_%s' % (zoneA, side)
        self.joints[zoneSide] = legJoints
        self.ikControllers[zoneSide] = self.legIkControllerList
        self.fkControllers[zoneSide] = self.legFkControllersList
        self.ikHandles[zoneSide] = ikHandle

        # delete ikfkShape
        pm.delete(ikFkNode)

        return self.legIkControllerList, self.legFkControllersList


    def foot_auto(self, side, zones=('leg','foot', 'toe'), planeAlign=None, *funcs):
        """
        # TODO: organize and optimize this Func
        # TODO: zone or zoneB?
        auto build a ik fk foot
        Args:
            side: left or right
            zone: foot
        """
        zoneA = zones[0]
        zoneB = zones[1]
        zoneC = zones[2]
        fkColor = 14 if side =='left' else 29
        toesJoints = [point for point in pm.ls() if re.match('^%s.*(%s).(?!_end)(?!0)(?!twist).*%s.*joint$' % (self.chName, zoneC, side), str(point))]
        toesZeroJoints = [point for point in pm.ls() if re.match('^%s.*(%s).(?!_end)(?=0)(?!twist).*%s.*joint$' % (self.chName, zoneC, side), str(point))]
        footJoints = [point for point in pm.ls() if re.match('^%s.*(%s).*((?!twist).).*%s.*joint$' % (self.chName, zoneB, side), str(point))]

        # arrange toes by joint chain p.e [[toea, toesa_Tip], [toeb, toeb_tip]]
        toesJointsArr = ARCore.arrangeListByHierarchy(toesJoints)

        # controllers and main lists
        footFkControllerList = []  # fk lists
        toesFkControllerList = []
        footIkControllerList = []  # ik lists
        toesIkControllerList = []
        footMainJointsList = []  # main lists
        toesMainJointsList = []

        footControllerNameList = []
        toeControllerNameList = []
        # create foot ctr
        for joint in footJoints:
            controllerName = str(joint).split('_')[1]
            logger.debug('foot controller name: %s' % controllerName)
            footFkCtr = joint.duplicate(po=True, name='%s_%s_%s_%s_fk_ctr' % (self.chName, controllerName, zoneB, side))[0]
            footMain = joint.duplicate(po=True, name='%s_%s_%s_%s_main_joint' % (self.chName, controllerName, zoneB, side))[0]

            # get transformMatrix and orient new controller TODO: function
            matrix = pm.xform(footFkCtr, ws=True, q=True, m=True)

            matrix = ARCore.orientToPlane(matrix, planeAlign)  # adjusting orient to plane zx
            pm.xform(footFkCtr, ws=True, m=matrix)  # new transform matrix with vector adjust

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
            footControllerNameList.append(controllerName)
            footFkControllerList.append(footFkCtr)
            footMainJointsList.append(footMain)

        # parent fk controller under leg
        self.legFkControllersList[-1].addChild(footFkControllerList[0])
        self.legMainJointList[-1].addChild(footMainJointsList[0])

        # twistJointsConnections
        if self.legTwistJoints:
            ARCore.twistJointsConnect(self.footTwstList, footMainJointsList[0], '%s_%s_%s_%s' % (self.chName, self.footTwstCtrName, self.footTwstZone, side), self.footpointCnstr)

        # TODO: function from joint, ik, fk, main?
        # create toe Fk and ik ctr
        # last foot fkCtr, easiest fot later access
        toeIkCtrParents = []  # list with first joint of toes chains
        toeMainParents = []
        for i, toe in enumerate(toesJointsArr):
            toeFkChain = []
            toeIkChain = []
            toeMainChain = []
            for joint in toe:
                controllerName = str(joint).split('_')[1]
                logger.debug('foot controller name: %s' % controllerName)
                toeFkCtr = joint.duplicate(po=True, name='%s_fk_%s_%s_%s_ctr' % (self.chName, zoneB, side, controllerName))[0]
                toeMainJnt = joint.duplicate(po=True, name='%s_main_%s_%s_%s_joint' % (self.chName, zoneB, side, controllerName))[0]
                toeIkCtr = joint.duplicate(po=True, name='%s_ik_%s_%s_%s_ctr' % (self.chName, zoneB, side, controllerName))[0]

                # get transformMatrix and orient new controller # TODO: function
                matrix = pm.xform(toeFkCtr, ws=True, q=True, m=True)
                matrix = ARCore.orientToPlane(matrix, planeAlign)  # adjusting orient to plane zx

                # apply transforms constrollers
                pm.xform(toeFkCtr, ws=True, m=matrix)
                pm.xform(toeIkCtr, ws=True, m=matrix)

                # fk ik toe control Shape
                shape = self.create_controller('%sShape' % str(toeFkCtr), '%sFk_%s' % (controllerName, side), 1, fkColor)
                toeFkCtr.addChild(shape.getShape(), s=True, r=True)
                pm.delete(shape)
                shape = self.create_controller('%sShape' % str(toeIkCtr), '%sFk_%s' % (controllerName, side), 1, fkColor)
                toeIkCtr.addChild(shape.getShape(), s=True, r=True)
                pm.delete(shape)

                # if joint Chain, reconstruct hierarchy
                if toeFkChain:
                    toeFkChain[-1].addChild(toeFkCtr)
                    toeIkChain[-1].addChild(toeIkCtr)
                    toeMainChain[-1].addChild(toeMainJnt)

                toeFkChain.append(toeFkCtr)  # this list is reset every loop iteration
                toeIkChain.append(toeIkCtr)
                toeMainChain.append(toeMainJnt)

                toesFkControllerList.append(toeFkCtr)  # review: this variable?
                toesIkControllerList.append(toeIkCtr)
                toesMainJointsList.append(toeMainJnt)
                toeControllerNameList.append(controllerName)

            # middle toe, useful later to general toe controller  # review
            if i == len(toesJointsArr) // 2:
                middleToeCtr = toeFkChain[0]
                middleToeCtrMatrix = pm.xform(middleToeCtr, q=True, ws=True, m=True)
                middleToeCtrIndex = i

            # construct foot hierarchy
            footFkControllerList[-1].addChild(toeFkChain[0])
            toeIkCtrParents.append(toeIkChain[0])  # ik ctr parent, for parent later in on ik ctrllers
            toeMainParents.append(toeMainChain[0])  # main parents
            logger.debug('toeIkchain: %s, %s' % (toeIkChain[0], type(toeIkChain[0])))
            logger.debug('toeIkCtrParents: %s' % (toeIkCtrParents))
            footMainJointsList[-1].addChild(toeMainChain[0])

        # ik foot ctr TODO: simplify this section
        # TODO: create the rest of the controllers here too
        footIkCtr = self.create_controller('%s_ik_%s_%s_foot_ctr' % (self.chName, zoneB, side), '%sIk_%s' % (zoneB, side), 1, 17)
        self.legCtrGrp.addChild(footIkCtr)
        footIkControllerList.append(footIkCtr)  # append joint to list
        for toeCtr in toeIkCtrParents:
            footIkCtr.addChild(toeCtr)

        #--start rest points-- # todo: rest points modular, a function
        footIkAttrTypes = ['heel', 'tilt', 'toes', 'ball', 'footRoll']  # list with hierarchy order restPointsVariable, names complete
        # add auto attributes
        for attr in footIkAttrTypes:
            pm.addAttr(footIkCtr, longName=attr, shortName=attr, type='float', defaultValue=0.0, k=True)

        pm.addAttr(footIkCtr, longName='showControls', shortName='showControls', type='bool', defaultValue=True, k=False)
        pm.setAttr('%s.showControls' % str(footIkCtr), channelBox=True)

        footFootRollCtr=[]  # list of footRoll ctr

        for ctrType in footIkAttrTypes[:-1]:
            if ctrType == 'tilt':
                for inOut in ('In', 'Out'):
                    footIkCtrWalk = self.create_controller('%s_ik_%s_%s_foot%s%s_ctr' % (self.chName, zoneB, side, ctrType.capitalize(), inOut),'foot%s%sIk_%s' % (ctrType.capitalize(),inOut, side), 1, 17)
                    footIkControllerList[-1].addChild(footIkCtrWalk)
                    footIkCtr.attr('showControls').connect(footIkCtrWalk.getShape().visibility)
                    footIkControllerList.append(footIkCtrWalk)
            else:
                footIkCtrWalk = self.create_controller('%s_ik_%s_%s_foot%s_ctr' % (self.chName, zoneB, side, ctrType.capitalize()), 'foot%sIk_%s' % (ctrType.capitalize(), side), 1, 17)
                footIkControllerList[-1].addChild(footIkCtrWalk)
                footIkCtr.attr('showControls').connect(footIkCtrWalk.getShape().visibility)
                footFootRollCtr.append(footIkCtrWalk)  # save footRoll controllers

                if ctrType == 'toes':
                    footToesIkCtr = footIkCtrWalk
                elif ctrType == 'ball':
                    footBallIkCtr = footIkCtrWalk

                footIkControllerList.append(footIkCtrWalk)

        # once all foot controllers are created, translate if necessary
        pm.xform(footIkCtr, ws=True, m=firstfootFkMatrix)
        # relocateBall cotr, aligned with middle toe
        footBallIkMatrix = [firstfootFkMatrix[0],firstfootFkMatrix[1],firstfootFkMatrix[2],firstfootFkMatrix[3],
                                            firstfootFkMatrix[4],firstfootFkMatrix[5],firstfootFkMatrix[6],firstfootFkMatrix[7],
                                            firstfootFkMatrix[8],firstfootFkMatrix[9],firstfootFkMatrix[10],firstfootFkMatrix[11],
                                            middleToeCtrMatrix[12], middleToeCtrMatrix[13], middleToeCtrMatrix[14], middleToeCtrMatrix[15]]
        pm.xform(footBallIkCtr, ws=True, m=footBallIkMatrix)

        # parent toes Ik ctr to footToes
        logger.debug('toeIkCtrParents: %s' % toeIkCtrParents)
        for toeCtr in toeIkCtrParents:
            footToesIkCtr.addChild(toeCtr)

        # --end rest points--
        for i in self.legIkControl.listRelatives(c=True, type='transform'):  # traspase childs from previous leg controller
            footBallIkCtr.addChild(i)

        pm.delete(self.legIkControl.firstParent())  # if foot, we do not need this controller
        self.legIkControllerList.remove(self.legIkControl)

        # toes general Controller ik Fk review: no side review: ik ctrllers  simplyfy with for
        toeFkGeneralController = self.create_controller('%s_fk_%s_%s_toeGeneral_ctr' % (self.chName, zoneB, side), 'toesFk', 1, fkColor)
        pm.xform(toeFkGeneralController, ws=True, m=middleToeCtrMatrix)  # align to middle individual toe review
        toeIkGeneralController = self.create_controller('%s_ik_%s_%s_toeGeneral_ctr' % (self.chName, zoneB, side), 'toesFk', 1, fkColor)
        pm.xform(toeIkGeneralController, ws=True, m=middleToeCtrMatrix)
        # parent and store to lists
        footFkControllerList[-1].addChild(toeFkGeneralController)
        footToesIkCtr.addChild(toeIkGeneralController)
        toesFkControllerList.append(toeFkGeneralController)
        toesIkControllerList.append(toeIkGeneralController)

        # fk Roots and autos
        ARCore.createRoots(footFkControllerList)
        ARCore.createRoots(footFkControllerList, 'auto')
        ARCore.createRoots(footIkControllerList)
        footRollAuto = ARCore.createRoots(footFootRollCtr, 'footRollAuto')  # review: all in the same if
        footIkAuto = ARCore.createRoots(footIkControllerList, 'auto')
        ARCore.createRoots(toesFkControllerList)
        toesFkAuto = ARCore.createRoots(toesFkControllerList, 'auto')
        ARCore.createRoots(toesIkControllerList)
        toesIkAuto = ARCore.createRoots(toesIkControllerList, 'auto')

        # toe Statick  # review, move fingers
        if len(toeMainParents) > 1:
            for i, toeMainP in enumerate(toeMainParents):
                if i != middleToeCtrIndex:
                    pm.parentConstraint(toeMainParents[middleToeCtrIndex], toeMainP, skipRotate=('x','y','z'), maintainOffset=True)

        # connect toes rotate general attributes and set limits
        for ikOrFk in [toesFkAuto, toesIkAuto]:
            toesGeneralCtrIkOrFk = toeFkGeneralController if ikOrFk == toesFkAuto else toeIkGeneralController

            logger.debug('toesGeneralCtrIkOrFk: %s, %s' % (toesGeneralCtrIkOrFk, type(toesGeneralCtrIkOrFk)))
            for i, iAuto in enumerate(ikOrFk):
                if zoneC in str(iAuto) and '%sGeneral' % zoneC not in str(iAuto):
                    for axis in ('X', 'Y', 'Z'):
                        toesGeneralCtrIkOrFk.attr('rotate%s' % axis).connect(iAuto.attr('rotate%s' % axis))

        # lock and hide attributes. after root creation
        ARCore.lockAndHideAttr(footIkControllerList[1:], True, False, True)
        ARCore.lockAndHideAttr(toesIkControllerList[-1], True, False, True)

        # footRollAuto __ rest points__
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
        # END footRollAuto __ rest points__

        ## BLEND ##
        # orient constraint main to ik or fk foot
        for i, mainJoint in enumerate(footMainJointsList):
            controllerName = footControllerNameList[i]
            if i == 0:
                # connect ik fk blend system, in a leg system only have one ik controller
                orientConstraint = pm.orientConstraint(footIkControllerList[-1], footFkControllerList[i], mainJoint, maintainOffset=True, name='%s_%s_%s_%s_mainBlending_orientConstraint' % (self.chName, controllerName, zoneB, side))
                self.ikFkshape.ikFk.connect(orientConstraint.attr('%sW0' % str(footIkControllerList[-1])))  # shape with bleeding attribute
                self.ikFkshape.ikFk.connect(footIkControllerList[i].visibility)  # all foot chain visibility

                # parent ikFk shape
                footIkControllerList[0].addChild(self.ikFkshape, s=True, add=True)

                # parent ikFk shape
                footFkControllerList[0].addChild(self.ikFkshape, s=True, add=True)

                self.plusMinusIkFk.output1D.connect(orientConstraint.attr('%sW1' % str(footFkControllerList[i])))
                self.plusMinusIkFk.output1D.connect(footFkControllerList[i].getShape().visibility)

            else:
                pm.orientConstraint(footFkControllerList[i], mainJoint, maintainOffset=True, name='%s_%s_%s_%s_mainBlending_orientConstraint' % (self.chName, controllerName, zoneB, side))

            ARCore.lockAndHideAttr(footFkControllerList[i], True, False, False)
            pm.setAttr('%s.radi' % footFkControllerList[i], channelBox=False, keyable=False)

            # connect to deform skeleton
            mainJoint.rename(str(footJoints[i]).replace('joint', 'main'))  # rename, useful for snap proxy model
            pm.orientConstraint(mainJoint, footJoints[i], maintainOffset=False, name='%s_%s_%s_%s_joint_orientConstraint' % (self.chName, controllerName, zoneB, side))

        ## TOES ##
        # main ik fk toes
        for i, mainJoint in enumerate(toesMainJointsList):
            controllerName = toeControllerNameList[i]
            orientConstraint = pm.orientConstraint(toesIkControllerList[i], toesFkControllerList[i], mainJoint, maintainOffset=True, name='%s_%s_%s_%s_mainBlending_orientConstraint' % (self.chName, controllerName, zoneB, side))

            self.ikFkshape.ikFk.connect(orientConstraint.attr('%sW0' % str(toesIkControllerList[i])))  # shape with bleeding attribute
            self.ikFkshape.ikFk.connect(toesIkControllerList[i].visibility)  # all foot chain visibility

            self.plusMinusIkFk.output1D.connect(orientConstraint.attr('%sW1' % str(toesFkControllerList[i])))
            self.plusMinusIkFk.output1D.connect(toesFkControllerList[i].visibility)

            pm.setAttr('%s.radi' % toesFkControllerList[i], channelBox=False, keyable=False)

            # connect to deform skeleton, review: point constraint toes main. strange behaviour
            mainJoint.rename(str(toesJoints[i]).replace('joint', 'main'))  # rename, useful for snap proxy model
            pm.orientConstraint(mainJoint, toesJoints[i], maintainOffset=False, name='%s_%s_%s_%s_joint_orientConstraint' % (self.chName, controllerName, zoneA, side))
            pm.pointConstraint(mainJoint, toesJoints[i], maintainOffset=False, name='%s_%s_%s_%s_joint_pointConstraint' % (self.chName, controllerName, zoneA, side))


        return footIkControllerList + toesIkControllerList, footFkControllerList + toesFkControllerList

    def hand_auto(self, side, zones=('arm', 'hand', 'finger'),planeAlign=None, *funcs):
        """
        auto build hand
        Args:
            side:
            zones:
            *funcs:
        Returns:
        """
        # zoneA = zones[0]
        zoneB = zones[1]
        zoneC = zones[2]
        fkColor = 14 if side == 'left' else 29
        fingerJoints = [point for point in pm.ls() if re.match('^%s.*(%s).(?!_end)(?!0)(?!twist).*%s.*joint$' % (self.chName, zoneC, side), str(point))]
        fingerZeroJoints = [point for point in pm.ls() if  re.match('^%s.*(%s).(?!_end)(?=0)(?!twist).*%s.*joint$' % (self.chName, zoneC, side), str(point))]
        handJoints = [point for point in pm.ls() if re.match('^%s.*(%s).*((?!twist).).*%s.*joint$' % (self.chName, zoneB, side), str(point))]

        # arrange toes by joint chain p.e [[toea, toesa_Tip], [toeb, toeb_tip]]
        fingerJointsArr = ARCore.arrangeListByHierarchy(fingerJoints)

        # controllers and main lists
        handFkControllerList = []  # fk lists
        handIkControllerList = []  # ik lists
        handMainJointsList = []  # main lists
        fingerMainJointsList = []

        handControllerNameList = []
        fingerControllerNameList = []
        # create foot ctr
        for joint in handJoints:
            controllerName = str(joint).split('_')[1]
            logger.debug('foot controller name: %s' % controllerName)
            footFkCtr = joint.duplicate(po=True, name='%s_%s_%s_%s_fk_ctr' % (self.chName, controllerName, zoneB, side))[0]
            footMain = joint.duplicate(po=True, name='%s_%s_%s_%s_main_joint' % (self.chName, controllerName, zoneB, side))[0]

            # get transformMatrix and orient new controller TODO: function
            matrix = pm.xform(footFkCtr, ws=True, q=True, m=True)

            matrix = ARCore.orientToPlane(matrix, planeAlign)  # adjusting orient to plane zx
            pm.xform(footFkCtr, ws=True, m=matrix)  # new transform matrix with vector adjust

            # fk control Shape
            shape = self.create_controller('%sShape' % str(footFkCtr), '%sFk_%s' % (controllerName, side), 1, fkColor)
            footFkCtr.addChild(shape.getShape(), s=True, r=True)
            pm.delete(shape)

            if not handFkControllerList:
                # save this matrix, to apply latter if necessary
                firstfootFkMatrix = matrix

            else:  # if more than 1 joint, reconstruct hierarchy
                handFkControllerList[-1].addChild(footFkCtr)
                handMainJointsList[-1].addChild(footMain)

            # save controllers
            handControllerNameList.append(controllerName)
            handFkControllerList.append(footFkCtr)
            handMainJointsList.append(footMain)

        # parent fk controller under leg
        self.legFkControllersList[-1].addChild(handFkControllerList[0])
        self.legMainJointList[-1].addChild(handMainJointsList[0])

        # twistJointsConnections
        if self.legTwistJoints:
            ARCore.twistJointsConnect(self.footTwstList, handMainJointsList[0],
                                      '%s_%s_%s_%s' % (self.chName, self.footTwstCtrName, self.footTwstZone, side),
                                      self.footpointCnstr)

        # create finger Fk and ik ctr
        # last hand fkCtr, easiest access later
        fingerMainParents = []
        for i, toe in enumerate(fingerJointsArr):
            fingerMainChain = []
            for joint in toe:
                controllerName = str(joint).split('_')[1]
                logger.debug('foot controller name: %s' % controllerName)
                fingerMainJnt = joint.duplicate(po=True, name='%s_main_%s_%s_%s_joint' % (self.chName, zoneB, side, controllerName))[0]

                # main finger control Shape
                shape = self.create_controller('%sShape' % str(fingerMainJnt), '%sFk_%s' % (controllerName, side), 1, fkColor)
                fingerMainJnt.addChild(shape.getShape(), s=True, r=True)
                pm.delete(shape)

                # if joint Chain, reconstruct hierarchy
                if fingerMainChain:
                    fingerMainChain[-1].addChild(fingerMainJnt)

                fingerMainChain.append(fingerMainJnt)
                fingerMainJointsList.append(fingerMainJnt)
                fingerControllerNameList.append(controllerName)

            # construct hand hierarchy
            fingerMainParents.append(fingerMainChain[0])  # main parents
            handMainJointsList[-1].addChild(fingerMainChain[0])

        # ik hand ctr
        handIkCtr = self.create_controller('%s_ik_%s_%s_foot_ctr' % (self.chName, zoneB, side), '%sIk_%s' % (zoneB, side), 1, 17)
        self.legCtrGrp.addChild(handIkCtr)
        handIkControllerList.append(handIkCtr)  # append joint to list

        for i in self.legIkControl.listRelatives(c=True, type='transform'):  # traspase childs from previous hand controller
            handIkCtr.addChild(i)

        pm.delete(self.legIkControl.firstParent())  # if foot, we do not need this controller
        self.legIkControllerList.remove(self.legIkControl)

        # fk Roots and autos
        ARCore.createRoots(handFkControllerList)
        ARCore.createRoots(handFkControllerList, 'auto')
        ARCore.createRoots(handIkControllerList)
        footIkAuto = ARCore.createRoots(handIkControllerList, 'auto')
        ARCore.createRoots(fingerMainJointsList)
        toesIkAuto = ARCore.createRoots(fingerMainJointsList, 'auto')

        ## BLEND ##
        # orient constraint main to ik or fk foot
        for i, mainJoint in enumerate(handMainJointsList):
            controllerName = handControllerNameList[i]
            if i == 0:
                # connect ik fk blend system, in a leg system only have one ik controller
                orientConstraint = pm.orientConstraint(handIkControllerList[-1], handFkControllerList[i], mainJoint, maintainOffset=True,
                                                       name='%s_%s_%s_%s_mainBlending_orientConstraint' % (self.chName, controllerName, zoneB, side))
                self.ikFkshape.ikFk.connect(orientConstraint.attr('%sW0' % str(handIkControllerList[-1])))  # shape with bleeding attribute
                self.ikFkshape.ikFk.connect(handIkControllerList[i].visibility)  # all foot chain visibility

                # parent ikFk shape
                handIkControllerList[0].addChild(self.ikFkshape, s=True, add=True)

                # parent ikFk shape
                handFkControllerList[0].addChild(self.ikFkshape, s=True, add=True)

                self.plusMinusIkFk.output1D.connect(orientConstraint.attr('%sW1' % str(handFkControllerList[i])))
                self.plusMinusIkFk.output1D.connect(handFkControllerList[i].getShape().visibility)

            else:
                pm.orientConstraint(handFkControllerList[i], mainJoint, maintainOffset=True,
                                                       name='%s_%s_%s_%s_mainBlending_orientConstraint' % (self.chName, controllerName, zoneB, side))

            ARCore.lockAndHideAttr(handFkControllerList[i], True, False, False)
            pm.setAttr('%s.radi' % handFkControllerList[i], channelBox=False, keyable=False)

            # connect to deform skeleton
            mainJoint.rename(str(handJoints[i]).replace('joint', 'main'))  # rename, useful for snap proxy model
            pm.orientConstraint(mainJoint, handJoints[i], maintainOffset=False, name='%s_%s_%s_%s_joint_orientConstraint' % (self.chName, controllerName, zoneB, side))

            ## finger ##
            # main ik fk toes
            for i, mainJoint in enumerate(fingerMainJointsList):
                controllerName = fingerControllerNameList[i]
                pm.setAttr('%s.radi' % mainJoint, channelBox=False, keyable=False)

                # connect to deform skeleton, review: point constraint toes main. strange behaviour
                mainJoint.rename(str(fingerJoints[i]).replace('joint', 'ctr'))
                pm.orientConstraint(mainJoint, fingerJoints[i], maintainOffset=False,  name='%s_%s_%s_%s_joint_orientConstraint' % (self.chName, controllerName, zoneC, side))
                pm.pointConstraint(mainJoint, fingerJoints[i], maintainOffset=False,  name='%s_%s_%s_%s_joint_pointConstraint' % (self.chName, controllerName, zoneC, side))

                if '1' in controllerName:
                    for zeroJoint in fingerZeroJoints:
                        if controllerName[:-1] in str(zeroJoint):
                            # create null grp to snap roxy model
                            fingerProxyNull = pm.group(empty=True, name=str(zeroJoint).replace('joint', 'main'))
                            # copy transforms
                            pm.xform(fingerProxyNull, ws=True, m=pm.xform(zeroJoint, ws=True, q=True, m=True))
                            # find parent
                            fingerParent = mainJoint.firstParent()
                            fingerParent.addChild(fingerProxyNull)  # make child of parent of the finger
                            # useful for snap proxy model
                            pm.aimConstraint(mainJoint, fingerProxyNull, aimVector=(zeroJoint.translateX.get(),0,0), worldUpType='objectrotation', worldUpObject=str(handMainJointsList[-1]))
                            # orient constraint, joint to froxy null
                            pm.orientConstraint(fingerProxyNull, zeroJoint, maintainOffset=False)


            return handIkControllerList, handFkControllerList + fingerMainJointsList


    def clavicle_auto(self, side,  zone='clavicle', *funcs):
        # TODO, detect parent from las ikFk chain
        fkColor = 14 if side == 'left' else 29
        clavicleJoints = [point for point in pm.ls() if re.match('^%s.*(%s).(?!_end)(?!0)(?!twist).*%s.*joint$' % (self.chName, zone, side), str(point))]
        clUpperArmJoint = clavicleJoints[-1].getChildren()[0]

        parent = self.legMainJointList[0].firstParent()  # get parent of the system

        parentChilds = [child for child in parent.listRelatives(c=True, type='transform') if (side in str(child)) and (self.lastZone in str(child).lower()) and not ('pole' in str(child))]

        logger.debug('childs: %s' %parentChilds)

        # store clavicle main joints here
        clavicleMainList = []

        for joint in clavicleJoints:
            controllerName = str(joint).split('_')[1]
            # create controller shape
            clavicleController = self.create_controller(str(joint).replace('joint', 'main'), '%sFk_%s' % (controllerName, side), 1, fkColor)
            pm.xform(clavicleController, ws=True, m=pm.xform(joint, q=True, ws=True, m=True))
            clavicleMainList.append(clavicleController)

        # hierarchy
        parent.addChild(clavicleMainList[0])

        # swing controller
        clavicleSwingCrt = self.create_controller('%s_%s_%s_swing_fk_ctr' % (self.chName, zone, side), 'swingFk_%s' % side, 1, fkColor)
        pm.xform(clavicleSwingCrt, ws=True, m=pm.xform(clUpperArmJoint, q=True, ws=True, m=True))  # set transforms
        clavicleMainList[-1].addChild(clavicleSwingCrt)
        clavicleMainList.append(clavicleSwingCrt)

        # parent ikFk chains to swing
        for ctr in (parentChilds):
            clavicleSwingCrt.addChild(ctr)
        # swing visibility
        self.plusMinusIkFk.output1D.connect(clavicleSwingCrt.getShape().visibility)

        # create roots
        ARCore.createRoots(clavicleMainList)
        clavicleAutoGrpList = ARCore.createRoots(clavicleMainList, 'auto')
        ARCore.createRoots([clavicleSwingCrt])

        # auto clavicle
        autoClavicleName = 'autoClavicleInfluence'
        pm.addAttr(self.ikFkshape, longName=autoClavicleName, shortName=autoClavicleName, minValue=0.0, maxValue=1.0, type='float', defaultValue=0.3, k=True)
        # nodes drive rotation by influence
        clavicleMultiplyNode = pm.createNode('multiplyDivide', name='%s_%s_%s_multiply' % (self.chName, zone, side))
        # todo: expose autoClavicle
        for axis in ('Y', 'Z'):
            # multiply by influence
            self.ikFkshape.attr(autoClavicleName).connect(clavicleMultiplyNode.attr('input1%s' % axis))
            self.legFkControllersList[0].attr('rotate%s' % axis).connect(clavicleMultiplyNode.attr('input2%s' % axis))
            # connect to auto clavicle
            clavicleMultiplyNode.attr('output%s' % axis).connect(clavicleAutoGrpList[0].attr('rotate%s' % axis))


        for i, joint in enumerate(clavicleJoints):
            # connect to deform joints
            clavicleMainList[i].rename(str(joint).replace('joint','ctr'))
            pm.pointConstraint(clavicleMainList[i], joint, maintainOffset=False)
            pm.orientConstraint(clavicleMainList[i], joint, maintainOffset=True)

        return [], clavicleMainList

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