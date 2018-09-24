import maya.api.OpenMaya as OpenMaya
import pymel.core as pm
import logging
import os
import time
import sys

logging.basicConfig()
logger = logging.getLogger('MeshFunctions:')
logger.setLevel(logging.INFO)
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

# def maya_useNewAPI():
#    pass

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

def listElements(item=None):
    """
    TODO: useful in code, not only for selection
    Select one object
    arg: item: MObject or string
    Returns:(list) [set(facesElement1), set(facesElement2), ...]
    """
    startTime = time.time()
    if not item:
        mSelection = OpenMaya.MGlobal.getActiveSelectionList()
    else:
        mSelection = OpenMaya.MSelectionList()
        mSelection.add(item)

    mDagPath = mSelection.getDagPath(0)
    mDagPath.extendToShape()

    mfnMesh = OpenMaya.MFnMesh(mDagPath)
    polyList = set(range(mfnMesh.numPolygons))  # first list with all index face. this will be deleted

    mItMeshPoly = OpenMaya.MItMeshPolygon(mDagPath)

    polyListElements = []

    while len(polyList):
        # convert to set ?
        # empty list to store a full element
        polyListElement = set()
        firstIndex = polyList.pop()  # get first index to operate
        polyListElement.add(firstIndex)  # append first poly index

        mItMeshPoly.setIndex(firstIndex)  # set to first element
        polyListConnect = set(mItMeshPoly.getConnectedFaces())  # faces connected to first element

        polyListElement, polyList = _getConnectedFaces(mItMeshPoly, polyListConnect, polyList, polyListElement, len(polyListElement))
        logger.debug('elementsDetect: polyListElement: %s' % polyListElement)

        polyListElements.append(polyListElement)
        logger.debug('elementDetect: polyListElements: %s' % polyListElements)

    logger.debug('elementDetect: polyListElements: %s' % polyListElements)

    logger.info('--- %s seconds ---' % (time.time() - startTime))
    return polyListElements

def _getConnectedFaces(mItMeshPoly, polyListConnect, polyList, polyListElement, PLELen):
    connectedFaces = set()  # store new border faces
    # loop from previous border faces
    connect = set()
    for i in polyListConnect:
        mItMeshPoly.setIndex(i)
        connect.update(mItMeshPoly.getConnectedFaces())  # get border faces from a face

    connect.difference_update(polyListElement)

    polyListElement.update(connect)
    polyList.difference_update(connect)

    connectedFaces.update(connect)

    if len(polyListElement) == PLELen:
        logger.debug('_getConnectedFaces: End')
        return polyListElement, polyList

    return _getConnectedFaces(mItMeshPoly, connectedFaces, polyList, polyListElement, len(polyListElement))

def listFaces(func=None):
    """
    List selected faces per mesh object
    Return: (dict) {meshObject1 : set(), meshObject2 : set(), ...}
    # TODO: return set per element
    """
    geometries = {}

    mSelection = OpenMaya.MGlobal.getActiveSelectionList()
    logger.debug('mSelection: %s, %s' % (mSelection, mSelection.length()))

    # itMselectionList
    mItSelection = OpenMaya.MItSelectionList(mSelection)
    logger.debug('mItSelection:%s' % (mItSelection))

    # iteration objects
    while not mItSelection.isDone():

        dagpath, component = mItSelection.getComponent()

        mItFaces = OpenMaya.MItMeshPolygon(dagpath, component)
        logger.debug('Count %s: %s' % (dagpath, mItFaces.count()))

        # store faces
        faces = set()

        # iteration components
        while not mItFaces.isDone():
            faces.add(mItFaces.index())
            # logger.debug(mItFaces.index())


            mItFaces.next(True)

        geometries[str(dagpath)] = faces

        mItSelection.next()

    return geometries