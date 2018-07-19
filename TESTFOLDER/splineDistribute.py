import logging
logging.basicConfig()
logger = logging.getLogger('Spline Distribute')
logger.setLevel(logging.DEBUG)

import pymel.core as pm

class splineDistribute(object):


    def __init__(self):

        super(splineDistribute, self).__init__()
        self.curves = []
        self.transformMesh = []

    def saveObjects(self):
        shapes = pm.ls(selection=True, type='mesh', dag=True)
        for shape in shapes:
            # shape are class type .Mesh
            transform = shape.getTransform()
            self.transformMesh.append(transform)
        logger.debug('Saved meshObjects: %s' % (','.join([str(meshObject) for meshObject in self.transformMesh])))
        self.curves = pm.ls(sl=True, type='nurbsCurve', dag=True)
        logger.debug('Saved nurbsCurves: %s' % (','.join([str(curve) for curve in self.curves])))

    def Distribute(self, *splines):
        pass

    def refresh(self, *splines):
        pass

    def addRandom(self, *splines):
        pass
