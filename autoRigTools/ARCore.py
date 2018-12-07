import pymel.core as pm
from maya import OpenMaya
from autoRigTools import ctrSaveLoadToJson

import logging
logging.basicConfig()
logger = logging.getLogger('ARCore:')
logger.setLevel(logging.DEBUG)


def createRoots(listObjects, suffix='root'):
    """
    Create root on elements, respecting their present hierarchy.
    Args:
        listObjects(list)(pm.Transform)(pm.Joint): list of transforms to create root, on joints set joint orient to 0
        suffix(str): suffix for the root grp

    Returns:
        roots(list): list of roots
    """
    roots = []
    for arg in listObjects:
        try:
            parent = arg.firstParent()
        except:
            parent = None
        # explanation: pm getTransformation gives transform matrix in object space.
        # so we need to use pm.xform()
        rootGrp = pm.group(em=True, name='%s_%s' % (arg, suffix))
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

def createController (name, controllerType, chName, path, scale=1.0, colorIndex=4):
    """
    Args:
        name: name of controller
        controllerType(str): from json controller types
        chName: name of json file
        path: path where is json file
    return:
        controller: pymel transformNode
        transformMatrix: stored position
    """
    controller, transformMatrix = ctrSaveLoadToJson.ctrLoadJson(controllerType, chName, path, scale, colorIndex)
    controller = pm.PyNode(controller)
    controller.rename(name)

    shapes = controller.listRelatives(s=True)
    # hide shape attr
    for shape in shapes:
        for attr in ('aiRenderCurve', 'aiCurveWidth', 'aiSampleRate', 'aiCurveShaderR', 'aiCurveShaderG', 'aiCurveShaderB'):
            pm.setAttr('%s.%s' % (str(shape), attr), channelBox=False, keyable=False)

    pm.xform(controller, ws=True, m=transformMatrix)
    return controller

def jointPointToController(joints, controller):
    """
    TODO: input scale too. first read if scale is connected to something, if it is, combine
    create a controller, create a root for the controller and point constraint to joint
    Args:
        joints(list(Joint)): joint where create controller
        controller(Transform): controller object
    Returns:
        list: [controller], [root], [pointConstraint]
    """
    controllerList = []
    rootList = []
    pointConstraintList=[]
    aimGrpList = []
    for i, joint in enumerate(joints):
        if i == 0:
            controllerDup = controller
        else:
            controllerDup = controller.duplicate()[0]

        pm.xform(controllerDup, ws=True, m=pm.xform(joint, ws=True, q=True, m=True))
        controllerRoot = createRoots([controllerDup])[0]
        # point constraint
        parentConstraint = pm.parentConstraint(joint, controllerRoot)

        # append to lists
        controllerList.append(controllerDup)
        rootList.append(controllerRoot)
        pointConstraintList.append(parentConstraint)
        # lock attr
        lockAndHideAttr(controllerDup, False, False, True)

    return controllerList, rootList, pointConstraintList

def lockAndHideAttr(obj, translate=False, rotate=False, scale=False):
    """
    lock and hide transform attributes
    # TODO: add limit operations
    Args:
        obj(pm.Trasform): Element to lock and hide
        translate(True): true, lock and hide translate
        rotate(True): true, lock and hide rotate
        scale(True): true, lock and hide scale
    """
    if isinstance(obj, list):
        itemList = obj
    else:
        itemList = []
        itemList.append(obj)

    for item in itemList:
        if translate:
            item.translate.lock()
            for axis in ('X', 'Y', 'Z'):
                pm.setAttr('%s.translate%s' % (str(item), axis), channelBox=False, keyable=False)
        if rotate:
            item.rotate.lock()
            for axis in ('X', 'Y', 'Z'):
                pm.setAttr('%s.rotate%s' % (str(item), axis), channelBox=False, keyable=False)
        if scale:
            item.scale.lock()
            for axis in ('X', 'Y', 'Z'):
                pm.setAttr('%s.scale%s' % (str(item), axis), channelBox=False, keyable=False)

def arrangeListByHierarchy(itemList):
    """
    Arrange a list by hierarchy
    p.e [[toea1, toea2, ...], [toeb, toeb_tip]]
    Args:
        itemList:
    Returns(list(list)): final list
    """
    def hierarchySize(obj):
        # key func for sort
        fullPath = obj.fullPath()
        sizeFullPath = fullPath.split('|')
        return len(sizeFullPath)

    toesJointsCopy = list(itemList)  # copy of the toes list
    toesJointsArr = []
    while len(toesJointsCopy):
        toeJoint = []
        firstJoint = toesJointsCopy.pop(0)
        toeJoint.append(firstJoint)
        for joint in firstJoint.listRelatives(ad=True):
            if joint in toesJointsCopy:
                toeJoint.append(joint)
                toesJointsCopy.remove(joint)

        # sort the list to assure a good order
        toesJointsArr.append(sorted(toeJoint, key=hierarchySize))
    logger.debug('arrangeListByHierarchy: sorted: %s' % toesJointsArr)

    return toesJointsArr

def attrBlending(ikNode, fkNode, blendAttr, nameInfo, *args):
    """
    create circuitry nodes to blend ik value to fk value
    Args:
        ikNode(pm.dependNode): node with stretch ik values
        fkNode(pm.dependNode): node with stretch Fk values
        blendAttr: attribute that will direct the blend
        nameInfo: str  with name info p.e('akona_lowerLeg_leg')
        args(pm.attributes): attributes to connect with the blend. pe. mainJoint.translateX (pm object)
    Return:
        last node with the blend info
    """
    # TODO: name scalable
    ikOutputType = 'outputX' if isinstance(ikNode, pm.nodetypes.MultiplyDivide) else 'distance' if isinstance(ikNode, pm.nodetypes.DistanceBetween) else 'output1D'
    fKoutputType = 'outputX' if isinstance(fkNode, pm.nodetypes.MultiplyDivide) else 'distance' if isinstance(fkNode, pm.nodetypes.DistanceBetween) else 'output1D'

    plusMinusBase=pm.createNode('plusMinusAverage', name='%s_blending_plusMinusAverage' % nameInfo)
    plusMinusBase.operation.set(2)  # substract
    ikNode.attr(ikOutputType).connect(plusMinusBase.input1D[0])
    fkNode.attr(fKoutputType).connect(plusMinusBase.input1D[1])
    # multiply
    multiplyNode = pm.createNode('multiplyDivide', name='%s_blending_multiplyDivide' % nameInfo)
    blendAttr.connect(multiplyNode.input1X)
    plusMinusBase.output1D.connect(multiplyNode.input2X)
    # plus Fk
    plusIkFkBlend = pm.createNode('plusMinusAverage', name='%s_blendingPlusFk_plusMinusAverage' % nameInfo)
    multiplyNode.outputX.connect(plusIkFkBlend.input1D[0])
    fkNode.attr(fKoutputType).connect(plusIkFkBlend.input1D[1])

    # connect to main attributes
    for arg in args:
        plusIkFkBlend.output1D.connect(arg)

    return plusIkFkBlend

def stretchIkFkSetup(fkObjList, fkDistances, nodeAttr, ikObjList, ikDistance, ikJoints, mainJoints, twsitMainJoints, nameInfo, main, poleVector=None):
    """
    create ik and fk stretch system with twistJoints, stretching by translate
    all the lists must be of the same len()
    Args:
        fkObjList : roots fk controllers that will stretch (no the first root) 2
        fkDistances(list(float)): list of distances between chain elements 2
        nodeAttr(pm.dagNode): shape with ikFk attribute, where fk stretch attribute will be added
        ikObjList(list): top object and lower object in a ik system 2
        ikDistance(float): maximum distance between top and lower element in a ik and fk system # calculate in the func?
        ikJoints(list): ikJoints that will stretch (no the first joint) 2
        char, zone, side: info
        mainJoints(list(pm.Joint)): MainJoints to connect the stretch (no the first joint) 2
        twsitMainJoints(list(list(pm.joints))) : lists with twist joints
        char, zone, side(str): name of character. zone os the system. side of the system
        main(PyNode): main controller
    TODO: less nodes, new node when all connections are used
    """
    # fk system
    # create attr
    attrName = 'fkStretch'
    pm.addAttr(nodeAttr, longName=attrName, shortName=attrName, minValue=.2, maxValue=5, type='float', defaultValue=1.0, k=True)
    outputFk = []
    for n, obj in enumerate(fkObjList):
        multiplyFk = pm.createNode('multiplyDivide', name='%s_fkStretch_multiplyDivide' % nameInfo)
        multiplyFk.input1X.set(fkDistances[n])
        nodeAttr.attr(attrName).connect(multiplyFk.input2X)

        multiplyFk.outputX.connect(obj.translateX)
        outputFk.append(multiplyFk)

    # conserveVolume using conditionalScaleFactor ->  1/conditionalScaleFactor   get inverse
    fkConserveVolumeScaleFactor = pm.createNode('multiplyDivide', name='%s_fkConserveVolume_multiplyDivide' % nameInfo)
    fkConserveVolumeScaleFactor.operation.set(2)  # set to divide
    fkConserveVolumeScaleFactor.input1X.set(1)
    nodeAttr.attr(attrName).connect(fkConserveVolumeScaleFactor.input2X)

    # need invert
    # invert  # todo: maybe this in conserveVolumeAnimNode func
    fkCVScaleFactorInvert = pm.createNode('plusMinusAverage', name='%s_fkStretch_Invert_plusMinusAverage' % nameInfo)
    fkCVScaleFactorInvert.operation.set(2)  # substract
    fkCVScaleFactorInvert.input1D[0].set(1)
    fkConserveVolumeScaleFactor.outputX.connect(fkCVScaleFactorInvert.input1D[1])



    # ik system
    if poleVector:  # if pole, create snap to pole
        snapPoleAttrStr = 'snapToPole'
        snapPoleAttr = pm.addAttr(nodeAttr, longName=snapPoleAttrStr, shortName=snapPoleAttrStr, minValue=0, maxValue=1, type='float', defaultValue=0.0, k=True)

    distanceBetweenPoleList=[]
    # distance between objetcs, and connect matrix
    distanceBetween = pm.createNode('distanceBetween', name='%s_ikStretch_distanceBetween' % nameInfo)
    scaleDistance = pm.createNode('multiplyDivide', name='%s_ikStretchScale_multiplyDivide' % nameInfo)
    scaleDistance.operation.set(2)  # divide
    distanceBetween.distance.connect(scaleDistance.input1X)
    main.scaleX.connect(scaleDistance.input2X)

    for i in range(len(ikObjList)):
        # use helpers to avoid cycle checks
        positionTrackIk = pm.group(empty=True, name='%s_ikStretch_track%s__grp' % (nameInfo, i+1))
        ikObjList[i].firstParent().addChild(positionTrackIk)
        pm.xform(positionTrackIk, ws=True, m=pm.xform(ikObjList[i], ws=True, q=True, m=True))

        positionTrackIk.worldMatrix[0].connect(distanceBetween.attr('inMatrix%s' % (i+1)))

        # for knee snap, extract distances from each point to pole vector
        if poleVector:
            distanceBetweenPole = pm.createNode('distanceBetween', name='%s_ikStretch_distancePole%s_distanceBetween' % (nameInfo, i+1))
            distancePoleScale = pm.createNode('multiplyDivide', name='%s_ikStretch_distanceScalePole%s_multiplyDivide' % (nameInfo, i+1))
            distancePoleScale.operation.set(2)  # divide
            positionTrackIk.worldMatrix[0].connect(distanceBetweenPole.inMatrix1)
            poleVector.worldMatrix[0].connect(distanceBetweenPole.inMatrix2)
            distanceBetweenPole.distance.connect(distancePoleScale.input1X)
            main.scaleX.connect(distancePoleScale.input2X)
            if ikJoints[i].translateX.get() < 0:
                invertValue = pm.createNode('multiplyDivide', name='%s_ikStretch_invertValue_multiplyDivide' % nameInfo)
                invertValue.input2X.set(-1)
                distancePoleScale.outputX.connect(invertValue.input1X)

                distancePoleScale = invertValue

            distanceBetweenPoleList.append(distancePoleScale)

    # conditional node
    conditionalScaleFactor = pm.createNode('condition', name='%s_ikStretch_stretchValue_conditional' % nameInfo)  # review stretchValue
    conditionalScaleFactor.operation.set(2)
    conditionalScaleFactor.colorIfFalseR.set(1)
    # connect distance to conditional
    scaleDistance.outputX.connect(conditionalScaleFactor.firstTerm)
    conditionalScaleFactor.secondTerm.set(abs(ikDistance))
    # scaleFactor
    multiplydivide = pm.createNode('multiplyDivide', name='%s_ikStretch_multiplyDivide' % nameInfo)
    multiplydivide.operation.set(2)  # set to divide
    scaleDistance.outputX.connect(multiplydivide.input1X)
    multiplydivide.input2X.set(abs(ikDistance))
    # connecto to conditional
    multiplydivide.outputX.connect(conditionalScaleFactor.colorIfTrueR)
    # multiply scale factor by joints x transform
    # TODO: create node every 3 connections
    outputIk = []
    conserveVolumeJointList = []
    for i, joint in enumerate(ikJoints):
        multiplyTranslate = pm.createNode('multiplyDivide', name='%s_ikStretch_jointValue_multiplyDivide' % nameInfo)
        conditionalScaleFactor.outColorR.connect(multiplyTranslate.input1X)
        multiplyTranslate.input2X.set(joint.translateX.get())

        # connect to joint
        # with pole Vector snap
        if poleVector:
            ikStretchOutput = attrBlending(distanceBetweenPoleList[i], multiplyTranslate, nodeAttr.attr(snapPoleAttrStr), nameInfo, joint.translateX)

            multiplyTranslate = ikStretchOutput
        else:
            multiplyTranslate.outputX.connect(joint.translateX)

        # save per joint output
        outputIk.append(multiplyTranslate)

        # create a list with all twist joints of the system
        if twsitMainJoints:
            conserveVolumeJointList += twsitMainJoints[i]

    # conserveVolume using conditionalScaleFactor ->  1/conditionalScaleFactor   get inverse
    ikConserveVolumeScaleFactor = pm.createNode('multiplyDivide', name='%s_conserveVolume_multiplyDivide' % nameInfo)
    ikConserveVolumeScaleFactor.operation.set(2)  # set to divide
    ikConserveVolumeScaleFactor.input1X.set(1)
    conditionalScaleFactor.outColorR.connect(ikConserveVolumeScaleFactor.input2X)
    # create animNode to control scale
    conserveVolumeAnimCurve = pm.createNode('animCurveTU', name='%s_conserveVolume_animCurveTU' % nameInfo)
    # draw curve
    conserveVolumeAnimCurve.addKeyframe(0, 0.3)
    conserveVolumeAnimCurve.addKeyframe((len(conserveVolumeJointList) - 1) // 2, 1.0)
    conserveVolumeAnimCurve.addKeyframe(len(conserveVolumeJointList) - 2, 0.3)
    # invert cv  -> (1-cv)
    iKInvConserveVolumeF = pm.createNode('plusMinusAverage', name='%s_conserveVolume_invertFactor_animCurveTU' % nameInfo)
    iKInvConserveVolumeF.operation.set(2)  # substract
    iKInvConserveVolumeF.input1D[0].set(1)
    ikConserveVolumeScaleFactor.outputX.connect(iKInvConserveVolumeF.input1D[1])

    for i, CVJoint in enumerate(conserveVolumeJointList):
        # ik
        ikCVNode = conserveVolumeAnimNode(conserveVolumeAnimCurve, i, iKInvConserveVolumeF, ikConserveVolumeScaleFactor, nameInfo)
        # fk
        fkCVNode = conserveVolumeAnimNode(conserveVolumeAnimCurve, i, fkCVScaleFactorInvert, fkConserveVolumeScaleFactor, nameInfo)
        # main blending
        # connect to joint
        attrBlending(ikCVNode, fkCVNode, nodeAttr.attr('ikFk'), '%s_conserveVolume' % nameInfo, CVJoint.scaleY, CVJoint.scaleZ)

    # to main joints formula: A+(B-A)*blend for joint, add twistBones, and stretch too
    for i, fkOut in enumerate(outputFk):
        # blending
        plusMinusToMain = attrBlending(outputIk[i], fkOut, nodeAttr.attr('ikFk'), '%s_stretch' % nameInfo, mainJoints[i].translateX)
        # stretch to twist joints

        if twsitMainJoints:
            # twist joints main translate review names
            multiplyDivideTwstJnt = pm.createNode('multiplyDivide', name='%s_mainTwistStretch_multiplyDivide' % nameInfo)
            multiplyDivideTwstJnt.operation.set(2)  # divide
            multiplyDivideTwstJnt.input2X.set(len(twsitMainJoints[i])-1)  # try change sign here review
            plusMinusToMain.output1D.connect(multiplyDivideTwstJnt.input1X)
            # connect to joints
            for twstJnt in twsitMainJoints[i][1:]:
                # first joint of the twistMainJoint does not has to move ()
                multiplyDivideTwstJnt.outputX.connect(twstJnt.translateX)


def conserveVolumeAnimNode(animCurve, varyTime, invFactor, Factor, nameInfo):
    """
    create circuity nodes to attach a curveAnim to control outputs values. useful for better results on stretch
    Args:
        animCurve(animNode): anim curve
        varyTime(index): frame to track value from the curve
        invFactor(node): plusMinusAverage node with 1-Factor
        Factor(node): scale Factor maxium
        nameInfo: list of three elements with name info p.e('akona', 'leg', 'lowerLeg')

    Returns: multiplyDivide node with final factor

    """

    outputType = 'outputX' if isinstance(Factor, pm.nodetypes.MultiplyDivide) else 'output1D'

    # frame cache
    CVFrameCache = pm.createNode('frameCache', name='%s_%s_%s_conserveVolume_frame' % (nameInfo[0], nameInfo[1], nameInfo[2]))
    animCurve.output.connect(CVFrameCache.stream)
    CVFrameCache.varyTime.set(varyTime)  # i
    # multiply frame cache
    multiplyFrameCache = pm.createNode('multiplyDivide', name='%s_%s_%s_conserveVolume_multiplyDivide' % (nameInfo[0], nameInfo[1], nameInfo[2]))
    CVFrameCache.varying.connect(multiplyFrameCache.input1X)
    invFactor.output1D.connect(multiplyFrameCache.input2X)
    # plus conserveVolume
    plusConVolum = pm.createNode('plusMinusAverage', name='%s_%s_%s_conserveVolume_plusMinusAverage' % (nameInfo[0], nameInfo[1], nameInfo[2]))
    multiplyFrameCache.outputX.connect(plusConVolum.input1D[0])
    Factor.attr(outputType).connect(plusConVolum.input1D[1])
    # divide volumeScalefactor / plusConserveVolum
    divideConVol = pm.createNode('multiplyDivide', name='%s_%s_%s_conserveVolume_divide_multiplyDivide' % (nameInfo[0], nameInfo[1], nameInfo[2]))
    divideConVol.operation.set(2)  # division
    Factor.attr(outputType).connect(divideConVol.input1X)
    plusConVolum.output1D.connect(divideConVol.input2X)

    return divideConVol


def calcDistances(pointList,vector=False):
    """
    Calculate de distance between the points in the given list. 0->1, 1->2, 2->3...
    Args:
        pointList(List)(pm.Transform):
        vector(bool): true: use vectors to calculate distances. False: read x value of each element. if points are joints, better use False
    Returns:
        (list): with distances
        (float): total distance
    """
    distancesList = []
    totalDistance = 0
    if vector:
        for i, point in enumerate(pointList):
            if i == len(pointList)-1:
                continue
            point1 = point.getTranslation('world')
            point2 = pointList[i+1].getTranslation('world')

            vector = point2 - point1
            vector = OpenMaya.MVector(vector[0],vector[1],vector[2])
            # length of each vector
            length = vector.length()

            distancesList.append(vector.length())
            totalDistance += length

    else:  # simply read X values
        for point in pointList[1:]:
            xtranslateValue = point.translateX.get()
            totalDistance += xtranslateValue
            distancesList.append(xtranslateValue)

    return distancesList, totalDistance


def syncListsByKeyword(primaryList, secondaryList, keyword=None):
    """
    arrange the secondary list by each element on the primary, if they are equal less the keyword
    if not keyword, the script will try to find one, p.e:
    list1 = ['akona_upperArm_left_joint','akona_foreArm_left_joint','akona_arm_end_left_joint']
    list2 = ['akona_upperArm_twist1_left_joint','akona_upperArm_twist2_left_joint','akona_foreArm_twist1_left_joint', 'akona_foreArm_twist2_left_joint']
    keyword: twist
    Returnsn : [['akona_upperArm_twist1_left_joint', 'akona_upperArm_twist2_left_joint'], ['akona_foreArm_twist1_left_joint', 'akona_foreArm_twist2_left_joint'], []]

    """
    filterChars = '1234567890_'
    # if not keyword try to find one
    if not keyword:
        count = {}
        # count how many copies of each word we have, using a dictionary
        for secondaryItem in secondaryList:
            for word in str(secondaryItem).split('_'):
                for fChar in filterChars:
                    word = word.replace(fChar, '')
                # if word is yet in dictionary, plus one, if not, create key with word and set it to one
                # explanation: dict.get(word, 0) return the value of word, if not, return 0
                count[word] = count.get(word, 0) + 1
        # key word must not be in primary list
        wordsDetect = [word for word in count if count[word] == len(secondaryList) and word not in str(primaryList[0])]

        if len(wordsDetect) != 1:
            logger.info('no keyword detect')
            return
        keyword = wordsDetect[0]

    arrangedSecondary = []
    # arrange by keyword
    for primaryItem in primaryList:
        actualList = []
        for secondaryItem in secondaryList:
            splitStr = str(secondaryItem).partition(keyword)
            indexCut = None
            for i, char in enumerate(splitStr[-1]):
                if char in filterChars:
                    indexCut = i + 1
                else:
                    break

            compareWord = splitStr[0] + splitStr[-1][indexCut:]
            if compareWord == str(primaryItem):
                actualList.append(secondaryItem)

        arrangedSecondary.append(actualList)

    return arrangedSecondary


def twistJointsConnect(twistMainJoints, trackMain, nameInfo, pointCnstr=None):
    """
    Connect and setup orient for twist joints
    Args:
        twistMainJoints(list)(pm.Joint): chain of twist joints
        trackMain(pm.Joint): main joint where trackGroup will be oriented constraint
        pointCnstr: object where the twistMainJoints[0] will be pointConstrained, if this arg is given, an extra group is created. to track correctly
        the main joint
        chName: name of the character
        zone: leg, arm
        side: left right
    return:
    """
    # if not pointCnstr use main joint
    if pointCnstr:
        twistRefGrp = pm.group(empty=True, name='%s_twistOri_grp' % nameInfo)
        pm.xform(twistRefGrp, ws=True, ro=pm.xform(twistMainJoints[0], ws=True, q=True, ro=True))
        pm.xform(twistRefGrp, ws=True, t=pm.xform(trackMain, ws=True, q=True, t=True))
        trackMain.addChild(twistRefGrp)

    else:
        pointCnstr = trackMain
        twistRefGrp = trackMain

    # group that will be used for store orientation, with a orientConstraint
    trackGroup = pm.group(empty=True, name='%s_twistOri_grp' % nameInfo)

    pm.xform(trackGroup, ws=True, m=pm.xform(twistMainJoints[0], ws=True, q=True, m=True))
    twistMainJoints[0].addChild(trackGroup)  # parent first joint of the chain

    # constraint to main
    twstOrientCntr = pm.orientConstraint(twistRefGrp,twistMainJoints[0], trackGroup, maintainOffset=True, name='%s_twistOri_orientContraint' % nameInfo)
    twstOrientCntr.interpType.set(0)
    # necessary for stretch, if not, twist joint does not follow main joints
    pm.pointConstraint(pointCnstr, twistMainJoints[0], maintainOffset=False, name='%s_twistPnt_pointConstraint' % nameInfo)
    # CreateIk
    twstIkHandle, twstIkEffector = pm.ikHandle(startJoint=twistMainJoints[0], endEffector=twistMainJoints[1], solver='ikRPsolver', name='%s_twist_ikHandle' % nameInfo)
    pointCnstr.addChild(twstIkHandle)
    # set Polevector to 0 0 0
    for axis in ('X', 'Y', 'Z'):
        twstIkHandle.attr('poleVector%s' % axis).set(0)

    #multiply x2 rotation
    multiplyX2 = pm.createNode('multiplyDivide', name='%s_twist_X2_multiplyDivide' % nameInfo)
    multiplyX2.input2X.set(2)
    trackGroup.rotateX.connect(multiplyX2.input1X)

    # nodes and connect to twist nodes rotations
    twstMultiplyDivide = pm.createNode('multiplyDivide', name='%s_twist_multiplyDivide' % nameInfo)
    twstMultiplyDivide.input2X.set(len(twistMainJoints) - 1)
    twstMultiplyDivide.operation.set(2)  # dividsion
    multiplyX2.outputX.connect(twstMultiplyDivide.input1X)
    # connect node to twist joint
    for k, twstJoint in enumerate(twistMainJoints):
        if k == 0:  # first joint nothing
            continue
        twstMultiplyDivide.outputX.connect(twstJoint.rotateX)


def relocatePole(pole, joints, distance=1):
    """
    relocate pole position for pole vector
    at the moment, valid for 3 joints.
    not calculate rotation
    Args:
        pole(pm.Transform): PyNode of pole
        joints(list)(pm.Transform): list of joints, pm nodes
        distance(float): distance from knee
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
                       poleVector.x * distance + position2[0], poleVector.y * distance + position2[1], poleVector.z * distance + position2[2], 1])



def snapCurveToPoints(points, curve, iterations=4, precision=0.05):
    """
    Snap curve to points moving CV's of the nurbsCurve
    Args:
        points(list): points where snap curve
        curve(pm.nurbsCurve): curve to snap
        iterations(int): number of passes, higher more precise. default 4
        precision(float): distance between point and curve the script is gonna take as valid. default 0.05
    """
    selection = OpenMaya.MSelectionList()
    selection.add(str(curve))
    dagpath = OpenMaya.MDagPath()
    selection.getDagPath(0, dagpath)

    mfnNurbsCurve = OpenMaya.MFnNurbsCurve(dagpath)

    for i in range(iterations):
        for joint in points:
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

def orientToPlane(matrix, plane=None):
    """
    Conserve the general orient of a matrixTransform, but aligned to a plane
    Args:
        controller(pm.transform): transform matrix
        plane(string): zx, xy, yz  lower case, first vector is the prefered vector
    """
    if not plane:
        logger.info('no plane')
        return matrix

    elif len(plane) > 2:
        logger.info('insert a valid plane')
        return matrix

    axisList = ['x', 'y', 'z']

    vectors = {}
    vIndex = 0
    # store initial vectors
    for axis in axisList:
        vectors[axis] = OpenMaya.MVector(matrix[vIndex], matrix[vIndex+1], matrix[vIndex+2])
        vIndex += 4

    # find resetable axis
    resetAxis = ''.join(axisList)  # convert axis list in axis string
    logger.debug('axisStr: %s' % resetAxis)
    for axis in plane:
        resetAxis = resetAxis.replace(axis, '')
    logger.debug('reset index: %s' % resetAxis)

    # reset the axis
    for key, vector in vectors.iteritems():
        if key == resetAxis:  # this is not necessary to reset
            continue
        setattr(vector, resetAxis, 0)
        vector.normalize()

    vectors[resetAxis] = vectors[plane[0]] ^ vectors[plane[1]]
    vectors[resetAxis].normalize()
    vectors[plane[1]] = vectors[resetAxis] ^ vectors[plane[0]]
    vectors[plane[1]].normalize()


    returnMatrix = [vectors[axisList[0]].x, vectors[axisList[0]].y, vectors[axisList[0]].z, matrix[3], vectors[axisList[1]].x, vectors[axisList[1]].y, vectors[axisList[1]].z, matrix[7],
                vectors[axisList[2]].x, vectors[axisList[2]].y, vectors[axisList[2]].z, matrix[11], matrix[12], matrix[13], matrix[14], matrix[15]]

    return returnMatrix

def stretchCurveVolume(curve, joints, nameInfo, main=None):
    curveInfo = pm.createNode('curveInfo', name='%s_curveInfo' % nameInfo)
    scaleCurveInfo = pm.createNode('multiplyDivide', name='%s_scaleCurve_curveInfo' % nameInfo)
    scaleCurveInfo.operation.set(2)  # divide
    # connect to scale compensate
    curveInfo.arcLength.connect(scaleCurveInfo.input1X)
    main.scaleX.connect(scaleCurveInfo.input2X)

    curve.worldSpace[0].connect(curveInfo.inputCurve)
    spineCurveLength = curve.length()

    # influence
    # create anim curve to control scale influence
    # maybe this is better to do with a curveAttr
    scaleInfluenceCurve = pm.createNode('animCurveTU', name='%s_stretch_animCurve' % nameInfo)
    scaleInfluenceCurve.addKeyframe(0, 0.0)
    scaleInfluenceCurve.addKeyframe(len(joints) // 2, 1.0)
    scaleInfluenceCurve.addKeyframe(len(joints) - 1, 0.0)

    for n, joint in enumerate(joints):
        jointNameSplit = str(joint).split('_')[1]

        multiplyDivide = pm.createNode('multiplyDivide', name='%s_%s_stretch_multiplyDivide' % (nameInfo, jointNameSplit))
        multiplyDivide.operation.set(2)  # divide
        multiplyDivide.input1X.set(spineCurveLength)
        scaleCurveInfo.outputX.connect(multiplyDivide.input2X)
        plusMinusAverage = pm.createNode('plusMinusAverage', name='%s_plusMinusAverage' % nameInfo)
        multiplyDivide.outputX.connect(plusMinusAverage.input1D[0])
        plusMinusAverage.input1D[1].set(-1)
        multiplyDivideInfluence = pm.createNode('multiplyDivide', name='%s_%s_stretch_multiplyDivide' % (nameInfo, jointNameSplit))
        plusMinusAverage.output1D.connect(multiplyDivideInfluence.input1X)
        # frame cache
        frameCache = pm.createNode('frameCache', name='%s_%s_stretch_frameCache' % (nameInfo, jointNameSplit))
        scaleInfluenceCurve.output.connect(frameCache.stream)
        frameCache.varyTime.set(n)
        frameCache.varying.connect(multiplyDivideInfluence.input2X)
        # plus 1
        plusMinusAverageToJoint = pm.createNode('plusMinusAverage', name='%s_%s_stretch_plusMinusAverage' % (nameInfo, jointNameSplit))
        multiplyDivideInfluence.outputX.connect(plusMinusAverageToJoint.input1D[0])
        plusMinusAverageToJoint.input1D[1].set(1)

        # connect to joint
        plusMinusAverageToJoint.output1D.connect(joint.scaleY)
        plusMinusAverageToJoint.output1D.connect(joint.scaleZ)

def aimUpVector(driver, driven, axis='y', space='object'):
    pass

def connectAttributes(driver, driven, attributes, axis):
    """
    connect the attributes of the given objects
    Args:
        driver: source of the connection
        driven: destiny of the connection
        attributes: attributes to connect p.e scale, translate
        axis: axis of the attribute p.e X, Y, Z
    """
    for attribute in attributes:
        for axi in axis:
            driver.attr('%s%s' % (attribute, axi)).connect(driven.attr('%s%s' % (attribute, axi)))