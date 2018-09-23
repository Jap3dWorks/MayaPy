import maya.cmds as mc


# todo: review: and pymel convertion or api
class japolyList(object):
    """
    Create dictionaries on face selections, based in objects and materials
    useful for more than 1 object selection.
    attr:
        objDic => a dictionary with objects and faces from selection
        matDic => a dictionary with materials and faces from selection
    """

    def __init__(self):
        self.objDic = {}
        self.matDic = {}
        iniSel = mc.ls(sl=True)
        self.polySel = mc.polyListComponentConversion(iniSel, fe=True, fv=True, fuv=True, ff=True, tf=True)

        # construct obj dictioanry
        # review: iterators fastest with api

        for fce in self.polySel:
            obj, face = fce.split('.')
            sFaces = None
            sFaces = self.objDic.get(obj)
            if sFaces is None:
                self.objDic[obj] = [fce]
            else:
                sFaces.append(fce)
                self.objDic[obj] = sFaces

        # construct mat dictionary

        for objM in self.objDic:
            grpIds = mc.ls(mc.listHistory(objM), type='groupId')
            shGrps = []

            # only one material object
            if 0 == len(grpIds):
                lsShape = mc.listRelatives(objM, s=True)
                shGrps = [mc.listConnections(lsShape, c=True, type='shadingEngine')[1]]

            # objects with more than one material
            else:
                shGrps = mc.listConnections(grpIds, type='shadingEngine')

            # polySelection initial flatten
            polySelFl = mc.ls(self.polySel, fl=True)

            # for material
            for shGrp in shGrps:
                material = mc.listConnections(shGrp + '.surfaceShader', c=True)[1]
                facesMat = []

                # only one material object
                if 0 == len(grpIds):
                    pNum = mc.polyEvaluate(f=True)
                    facesMat = mc.ls((objM + '.f[0:' + str(pNum - 1) + ']'), fl=True)

                # objects with more than one material
                else:
                    mc.select(clear=True)
                    mc.hyperShade(objects=material)
                    facesMat = mc.ls(sl=True, fl=True)
                    mc.select(clear=True)

                # compare faces in initial selection
                for fce in facesMat:
                    if fce in polySelFl:
                        sFaces = None
                        sFaces = self.matDic.get(material)
                        if sFaces == None:
                            self.matDic[material] = [fce]
                        else:
                            sFaces.append(fce)
                            self.matDic[material] = sFaces

                # remove flatten lists in dictionaries
                mc.select(self.matDic[material], r=True)
                flatenFaces = mc.ls(sl=True)
                self.matDic[material] = flatenFaces
