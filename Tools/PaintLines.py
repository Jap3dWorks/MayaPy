from maya import cmds
import maya.api.OpenMaya as om

# TODO: Convert in plug in. node. with vertex face projection,
# cut per edge of under poly surface

class paintLines(object):
    
    def __init__(self):
        super(paintLines, self).__init__()
		# curves = curve : [[poaition],[vectorX]],...
        self.curves={}
        self.getPos()
    
    def getPos(self):
        """
        get all curves and create a dictionary with first point position and x vector direction
        """
        CurveObjShpes = cmds.ls(sl=True, type = 'nurbsCurve', dag= True)
        
        for CurveObjShpe in CurveObjShpes:
            CurveObjTr = cmds.listRelatives(CurveObjShpe, p = True) [0]
            COiniP, COsecondP = ['%s.cv[0]' %CurveObjTr, '%s.cv[1]' %CurveObjTr]
            
            coPosP1 = cmds.xform (COiniP, q=True, t=True, ws=True)
            coPosP2 = cmds.xform(COsecondP, q=True, t=True, ws=True)
            coVecX = [coPosP2[0] - coPosP1[0], coPosP2[1] - coPosP1[1], coPosP2[2] - coPosP1[2]]
            
            self.curves[CurveObjTr] = {'position':coPosP1, 'vectorX':coVecX}
            
    def createGeometry(self, size = 12, divisions = 50):
        for curv, val in self.curves.iteritems():
            plane, shape = cmds.polyPlane (h = size, w = size, sh = 1, sw = 1)
            print 'pplane is ',plane
            polyPlane = cmds.listConnections(shape, d = True, type='polyPlane')
            #orient plane
            vectorX = om.MVector(val['vectorX'][0], val['vectorX'][1], val['vectorX'][2])
            vectorX.normalize()
            vectorY = om.MVector(0,1,0)
            vectorZ = vectorX ^ vectorY
            cmds.xform(plane, ws=True, m =(vectorX.x,vectorX.y,vectorX.z,0, vectorY.x, vectorY.y, vectorY.z, 0, vectorZ.x, vectorZ.y, vectorZ.z,0, val['position'][0], val['position'][1], val['position'][2], 1))
            #extrude
            extrudeNde = cmds.polyExtrudeEdge('%s.e[2]' %plane, inputCurve = curv, divisions = divisions)[0]
            print extrudeNde
            val['geometry'] = plane
            val ['shape'] = shape
            val['extrudeNde'] = extrudeNde
            val['polyPlane'] = polyPlane
            self.curves[curv] = val
            self.createUv(mesh = plane)
        cmds.select(self.curves.keys(), r=True)
            
			
    def editGeometry(self, size = 12, divisions = 50, *args):
        selection = args
        if not len(args):
            selection = cmds.ls(sl = True)
        for sel in selection:
            if sel in self.curves:
                cmds.polyPlane(self.curves[sel]['shape'], e = True, h = size, w = size)
                cmds.polyExtrudeEdge(self.curves[sel]['extrudeNde'], e=True,divisions = divisions)
                plane = self.curves[sel]['geometry']
                self.createUv(mesh = plane)
        cmds.select(selection, r = True)
                
    def createUv(self,mesh):
        cmds.polyForceUV(mesh, unitize = True)
        edges = cmds.polyEvaluate(mesh, e = True)
        cmds.select('%s.e[2:%s]' %(mesh, (edges-1)), r=True)
        cmds.StitchTogether()
        bbox = cmds.polyEvaluate(mesh, bc2 = True)
        if bbox[0]>bbox[1]:
            cmds.polyEditUV (mesh, r = True, a = 90)
        cmds.polyNormalizeUV(mesh,normalizeType = 1, pa = True, cot = False, nd = 1)
        cmds.unfold(mesh, i = 5000, ss=0.001, gb = 0, pub = False, ps = False, oa = 1, us = False)
        cmds.select(cl=True)