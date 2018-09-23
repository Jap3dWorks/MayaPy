import maya.api.OpenMaya as OpenMaya
import logging
logging.basicConfig()
logger = logging.getLogger('Component Iterator:')
logger.setLevel(logging.DEBUG)

def intersectionAPI1():
    """

    Returns:

    """
    # documentation: http://www.fevrierdorian.com/blog/post/2011/07/31/Project-a-mesh-to-another-with-Maya-API-%28English-Translation%29
    mSelList = OpenMaya1.MSelectionList()
    OpenMaya1.MGlobal.getActiveSelectionList(mSelList)

    dagPath0 = OpenMaya1.MDagPath()

    mSelList.getDagPath(0, dagPath0)
    dagPath0.extendToShape()

    mfnMesh0 = OpenMaya1.MFnMesh(dagPath0)

    print mfnMesh0.numPolygons

    # grid = mfnMesh.autoUniformGridParams()
    raySource = OpenMaya1.MFloatPoint(0, 0, 0)
    rayDirection = OpenMaya1.MFloatVector(0, 1, 0)

    triangles = OpenMaya1.MIntArray()
    trianglesVertex = OpenMaya1.MIntArray()
    mfnMesh0.getTriangles(triangles, trianglesVertex)

    trisList = OpenMaya1.MIntArray()
    # list triangles like ((face,tri),(face,tri)...)
    polyRange = OpenMaya1.MIntArray()
    for i, val in enumerate(triangles):
        polyRange.append(i)
        for index in range(val):
            trisList.append(i)
            trisList.append(index)

    print (trisList)
    print (polyRange)

    mfnMesh0.sortIntersectionFaceTriIds(polyRange, trisList)

    # Explanation: this is the way to create a pointer in memory and have access later -> hitFaceUtil.getInt(hitFacePtr)
    hitFaceUtil = OpenMaya1.MScriptUtil(0)
    hitFacePtr = hitFaceUtil.asIntPtr()

    idsSorted = False
    testBothDirections = False
    faceIds = None
    triIds = None
    accelParams = None
    hitRayParam = None
    hitTriangle = None
    hitBary1 = None
    hitBary2 = None
    maxParamPtr = 99999999
    hitPoint = OpenMaya1.MFloatPoint()
    space = OpenMaya1.MSpace.kWorld

    # http://zoomy.net/2009/07/31/fastidious-python-shrub/
    hit = mfnMesh0.closestIntersection(raySource,
                                       rayDirection,
                                       faceIds,
                                       triIds,
                                       idsSorted,
                                       space,
                                       maxParamPtr,
                                       testBothDirections,
                                       accelParams,
                                       hitPoint,
                                       hitRayParam,
                                       hitFacePtr,
                                       hitTriangle,
                                       hitBary1,
                                       hitBary2)
    print (hit)
    print ((hitPoint.x, hitPoint.y, hitPoint.z), hitFaceUtil.getInt(hitFacePtr), hitTriangle, hitBary1, hitBary2)

def intersectionPymel():
    selection = pm.ls(sl=True)[0]
    shape = selection.getShape()

    # explanation: pymel understand OpenMaya data types.
    pmPoint = OpenMaya1.MPoint(0, 0, 0)
    pmVector = OpenMaya1.MVector(0, 1, 0)
    intrsctn = shape.intersect(pmPoint, pmVector, 0.01, 'world')
    print intrsctn


if __name__=='__main__':
    print listFaces()