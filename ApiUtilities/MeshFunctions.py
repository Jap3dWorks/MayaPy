import maya.api.OpenMaya as OpenMaya
import maya.OpenMaya as OpenMaya1
import logging

logging.basicConfig()
logger = logging.getLogger('MeshFunctions:')
logger.setLevel(logging.DEBUG)
import pymel.core as pm

"""
interesting methods
# MDagPathArray
# MItMeshVertex
# MFnMesh:
    allIntersections()
    autoUniformGridParams()
    addPolygon()
    assignUVs()
    create()
    createBlindDataType() ?
    getHoles()
    getConnectedShaders()
# MItMeshPolygon()
    setIndex()
    getConnectedFaces()
# MPointArray 
# OpenMaya1.MScriptUtil().asIntPtr() -> int variables
"""


def vertList(mesh=None, objectSpace=False):
    """
    TODO: undo queue
    Opetate on vertes of a poligonal shape
    arg:
        mesh: tuple or list mesh to operate, transform node
        objectSpace: default False
    return:
        MPointArray vertex positions
    """
    if not mesh:
        mSelList = OpenMaya.MGlobal.getActiveSelectionList()

    else:
        assert isinstance(mesh, tuple) or isinstance(mesh, list), 'mesh arg must be tuple or list'
        mSelList = OpenMaya.MSelectionList()
        for i in mesh:
            mSelList.add(i)

    mSelList_It = OpenMaya.MItSelectionList(mSelList).setFilter(OpenMaya.MFn.kTransform)

    mPointTotal = []

    while not mSelList_It.isDone():
        dagPath = mSelList_It.getDagPath()
        dagPath.extendToShape()  # extend to shape
        print dagPath

        mfnMesh = OpenMaya.MFnMesh(dagPath)  # functions to operate on a polygonal shape
        mPointArray = mfnMesh.getPoints(OpenMaya.MSpace.kObject) if objectSpace else mfnMesh.getPoints(
            OpenMaya.MSpace.kWorld)  # get vertex positions in world space

        logger.debug(mPointArray)
        mPointTotal.append(mPointArray)

        mSelList_It.next()

    return mPointTotal


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


def maya_useNewAPI():
    pass
def intersectionAPI2():
    """
    Select two objects. the second shot a ray at its X axis over the first.
    return: id face collision
    """
    mSelList = OpenMaya.MGlobal.getActiveSelectionList()

    dagPath0 = mSelList.getDagPath(0)
    dagPath0.extendToShape()

    mfnMesh0 = OpenMaya.MFnMesh(dagPath0)

    dagPath1 = mSelList.getDagPath(1)
    mfnTransform = OpenMaya.MFnTransform(dagPath1)

    testBothDirections = False
    maxParamPtr = 9999999.0
    space = OpenMaya.MSpace.kWorld
    spaceVector = OpenMaya.MSpace.kTransform

    raySource = OpenMaya.MFloatPoint(mfnTransform.rotatePivot(space))
    # print raySource

    rayDirectionMatrix = mfnTransform.rotation(spaceVector).asMatrix()

    rayDirection = OpenMaya.MFloatVector(rayDirectionMatrix[0], rayDirectionMatrix[1], rayDirectionMatrix[2])
    # http://zoomy.net/2009/07/31/fastidious-python-shrub/
    hit = mfnMesh0.closestIntersection(raySource,
                                       rayDirection,
                                       space,
                                       maxParamPtr,
                                       testBothDirections
                                       )
    pm.select('%s.f[%s]' % (dagPath0, hit[2]))
    print (hit)


def intersectionPymel():
    selection = pm.ls(sl=True)[0]
    shape = selection.getShape()

    # explanation: pymel understand OpenMaya data types.
    pmPoint = OpenMaya1.MPoint(0, 0, 0)
    pmVector = OpenMaya1.MVector(0, 1, 0)
    intrsctn = shape.intersect(pmPoint, pmVector, 0.01, 'world')
    print intrsctn


def elementsDetect():
    mSelection = OpenMaya.MGlobal.getActiveSelectionList()

    mDagPath = mSelection.getDagPath(0)
    mDagPath.extendToShape()

    mfnMesh = OpenMaya.MFnMesh(mDagPath)
    polyList = range(mfnMesh.numPolygons)  # first list with all index face. this will be deleted

    mItMeshPoly = OpenMaya.MItMeshPolygon(mDagPath)

    polyListElements = []

    while len(polyList):
        # convert to set ?
        # empty list to store a full element
        polyListElement =[]
        polyListElement.append(polyList[0])  # append first poly index

        mItMeshPoly.setIndex(polyList[0])  # set to first element of the list
        polyListConnect = mItMeshPoly.getConnectedFaces()  # faces connected to first element

        polyListElement, polyList = getConnectedFaces(mItMeshPoly, polyListConnect, polyList, polyListElement, len(polyListElement))

        polyListElements.append(polyListElement)

    logger.debug('elementDetect: polyListElements: %s' % polyListElements)

def getConnectedFaces(mItMeshPoly, polyListConnect, polyList, polyListElement, PLELen):
    connectedFaces = []  # store new border faces
    # loop from previous border faces
    for i in polyListConnect:
        mItMeshPoly.setIndex(i)
        connect = mItMeshPoly.getConnectedFaces()  # get border faces from a face
        connectedFaces.extend([i for i in connect if i not in connectedFaces])

        polyListElement.extend([i for i in connect if i not in polyListElement])

        polyList = [i for i in polyList if i not in polyListElement]

    if len(polyListElement) == PLELen:
        logger.debug('getConnectedFaces: End')
        return polyListElement, polyList

    return getConnectedFaces(mItMeshPoly, connectedFaces, polyList, polyListElement, len(polyListElement))

