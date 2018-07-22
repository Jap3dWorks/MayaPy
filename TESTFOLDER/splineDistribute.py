from __future__ import division

import logging
logging.basicConfig()
logger = logging.getLogger('Spline Distribute')
logger.setLevel(logging.DEBUG)

import random

import pymel.core as pm

class splineDistribute(object):


    def __init__(self):

        super(splineDistribute, self).__init__()
        self.curves = [] # dictionary
        self.transformMesh = []
        self.curveGroups = set([])  # group per curve with all the objects created

    def saveObjects(self, reset=True):
        if reset:
            # reset lists to entry of new objects
            self.curves[:] = []
            self.transformMesh[:] = []
            self.curveGroups.clear()
        shapes = pm.ls(selection=True, type='mesh', dag=True)
        for shape in shapes:
            # shape are class type .Mesh
            transform = shape.getTransform()
            self.transformMesh.append(transform)
        logger.debug('Saved meshObjects: %s' % (','.join([str(meshObject) for meshObject in self.transformMesh])))
        self.curves = pm.ls(sl=True, type='nurbsCurve', dag=True)
        logger.debug('Saved nurbsCurves: %s' % (','.join([str(curve) for curve in self.curves])))

    def distribute(self, increment, bbox=False, *args, **kwargs):
        if not (self.curves and self.transformMesh):
            logger.info('No curves were saved, please excecute .saveObjects() before')
            return
        for curve in self.curves:
            currentCurvePos = 0.0
            if increment >= curve.length():
                logger.info('Increment value is higher than %s length' % curve)
                continue
            curveGrp = pm.createNode('transform', n='%sGrp' % curve)
            self.curveGroups.add(curveGrp)
            while currentCurvePos < 1.0:
                random.shuffle(self.transformMesh)  # random items
                logger.debug('currentCurvePos value is: %s' % currentCurvePos)
                if bbox:
                    currentCurvePos += self.boundingBoxObject(self.transformMesh[0])/curve.length()
                # validateChecks
                    if currentCurvePos > 1:
                        logger.debug('currentCurvePos value is bigger than 1: %s : %s' % (curve, currentCurvePos))
                        break
                    if currentCurvePos <= 0:
                        logger.warning('currentCurvePos is not incrementing its value: %s' % currentCurvePos)
                        break

                # create duplicate obj
                trnfMesh = pm.duplicate(self.transformMesh[0])[0]
                logger.debug('trnsMesh is type: %s' % type(trnfMesh))
                # group object and parent it in its respective curveGrp
                trnfGrp = pm.createNode('transform', n='%sOffset' % trnfMesh)
                motionPath = pm.PyNode(pm.pathAnimation(trnfGrp, c=curve, follow=True, followAxis='x', upAxis='y', fractionMode=True))
                motionPath.setUStart(currentCurvePos)
                pm.parent(trnfGrp, curveGrp)
                # pm.disconnectAttr('%s_uValue.output' % motionPath, motionPath.uValue)
                pm.delete('%s_uValue' % str(motionPath))
                # pos group and set transforms to zero
                pm.parent(trnfMesh, trnfGrp)
                trnfMesh.setTranslation((0,0,0), space='object')
                trnfMesh.setRotation((0,0,0))

                self.randomizerItem(trnfMesh, *args, **kwargs)

                currentCurvePos += increment / curve.length()  # this syntax type doesn't work on Int
                if bbox:
                    currentCurvePos += self.boundingBoxObject(self.transformMesh[0]) / curve.length()
                # validateChecks
                if currentCurvePos > 1:
                    logger.debug('currentCurvePos value is bigger than 1: %s : %s' % (curve, currentCurvePos))
                    break
                if currentCurvePos <= 0:
                    logger.warning('currentCurvePos is not incrementing its value: %s' % currentCurvePos)
                    break

    def randomizerItem(self, item, tX=0.0, tY=0.0, tZ=0.0, roX=0.0, roY=0.0, roZ=0.0, sX=0.0, sY=0.0, sZ=0.0, sXZeq=False):
        # here a process to randomize items
        if not isinstance(item, pm.nodetypes.Transform):
            return logger.warning('no valid item to randomizerItem %s : is not pm.nodetypes.Transform' % item)

        # set translate Random
        if tX != 0.0 or tY != 0.0 or tZ != 0.0:
            item.setTranslation([random.random()*tX, random.random()*tY, random.random()*tZ], space='object')
            logger.debug('Translate randomized for %s:' % item)
        # set rotation Random
        if roX != 0.0 or roY != 0.0 or roZ != 0.0:
            item.setRotation([random.random()*roX, random.random()*roY, random.random()*roZ], space='object')
            logger.debug('Rotate randomized for %s:' % item)
        # set scale Random
        if sX != 0.0 or sY != 0.0 or sZ != 0.0:
            item.setScale([random.random()*sX, random.random()*sY, random.random()*sZ])
            logger.debug('Scale randomized for %s:' % item)
            # if sXZeq copy x value to z value
            if sXZeq:
                item.scaleZ.set(item.scaleX.get())

    def boundingBoxObject(self, object):
        group=pm.group(empty=True, parent=object)
        try:
            pm.parent(group, pm.listRelatives(object, parent=True))
        except:
            pm.parent(group, world=True)
        pm.parent(object, group)
        object.resetFromRestPosition()
        boundingBox = self.transformMesh[0].getBoundingBox(space='object')
        pm.ungroup(group)
        return abs(((boundingBox[1][0] - boundingBox[0][0]) / 2))


    def bakePositions(self, *splines):
        # get mesh type dag bjects, the we search all the groups and ungroup
        for curveGroup in self.curveGroups:
            for shape in (pm.ls( curveGroup, dag=True, type='mesh')):
                while True:
                    if shape.getTransform().getParent() != curveGroup:
                        pm.ungroup(shape.getTransform().getParent())
                    else:
                        logger.debug('was baked: %s' % shape.getTransform())
                        break
