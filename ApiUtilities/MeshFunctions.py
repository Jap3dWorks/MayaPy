import maya.api.OpenMaya as OpenMaya

# test:
# MDagPathArray
# MItMeshVertex
# MFnMesh
# MPointArray

def vertexFunc():
    """
    Opetate on vertes of a poligonal shape
    """
    mSelList = OpenMaya.MGlobal.getActiveSelectionList()
    
    mSelList_It = OpenMaya.MItSelectionList(mSelList).setFilter(OpenMaya.MFn.kTransform)
    
    while not mSelList_It.isDone():
        dagPath = mSelList_It.getDagPath()
        dagPath.extendToShape() # extend to shape
        print dagPath
        
        mfnMesh = OpenMaya.MFnMesh(dagPath) # functions to operate on a poligonal shape
        mPointArray = mfnMesh.getPoints() # get vertex positions
        # iterate mPointArray
        for i, val in enumerate(mPointArray):
            # print val
            val.x += 3 # modify vertex position
            print '%s\n==========' % val
            
            mfnMesh.setPoint(i, val) # insert new vertex position
        
        mSelList_It.next()
    

enevMessage = None
if __name__ == '__main__':
    vertexFunc()
    
    
