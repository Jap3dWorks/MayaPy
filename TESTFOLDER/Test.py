import maya.api.OpenMaya as OpenMaya
import maya.cmds as cmds

def curveCreateEP():
    mselList = OpenMaya.MGlobal.getActiveSelectionList()
    
    mFndagObject = OpenMaya.MFnDagNode()
    dependNode = mFndagObject.create('transform', 'curve')
    
    # points
    mPointArray = OpenMaya.MPointArray()
    mPointArray.append(OpenMaya.MPoint(0,0,0))
    mPointArray.append(OpenMaya.MPoint(10,0,0))
    mPointArray.append(OpenMaya.MPoint(20,10,0))
    mPointArray.append(OpenMaya.MPoint(20,20,0))
    mPointArray.append(OpenMaya.MPoint(20,30,0))
    
    mFnCurve = OpenMaya.MFnNurbsCurve()
    mFnCurve.createWithEditPoints(mPointArray, 7, 1, False, False, False, dependNode)
 
    
    # get area
    area = mFnCurve.area(1.0)
    print area



def curveCreateCV(cv=((0,0,0), (5,0,0), (10,0,0), (20,10,5), (20,15,10), (20,20,15)), knots=((0.0), (0.0), (0.0), (3), (7), (10), (10), (10))):
    """
    Create a curve and snap an object to the center
    Args:
        cv: Curve vertex
        knots: Knots
    """
    mFndagObject = OpenMaya.MFnDagNode()
    dependNode = mFndagObject.create('transform', 'curve')
    
    # CV
    mPointArray = OpenMaya.MPointArray(cv)
    
    # knots
    KnotArray = OpenMaya.MDoubleArray(knots)
    # create curve
    mFnCurve = OpenMaya.MFnNurbsCurve()
    mFnCurve.create(mPointArray, KnotArray, 3, 1, False, False, dependNode)

    mfntransformCurve = OpenMaya.MFnTransform(dependNode)
    mfntransformCurve.setTranslation(OpenMaya.MVector(15, 15, 15), 2)
    mfntransformCurve.setRotation(OpenMaya.MEulerRotation(OpenMaya.MVector(15, 15, 15)), 1)

    # if mfn is not set with dag path, cant do world transforms
    curveDagpath = mfntransformCurve.getPath()
    mFnCurve.setObject(curveDagpath)

    print ('dag path: %s' % curveDagpath)

    
    # get area
    area = mFnCurve.area(1.0)
    print (area)

    # get lenght
    curveLenght = mFnCurve.length()
    print (curveLenght)

    middlePoint = mFnCurve.getPointAtParam(5.0, OpenMaya.MSpace.kWorld)
    middleNormal = mFnCurve.normal(5.0, OpenMaya.MSpace.kWorld)
    middleNormal.normalize()
    middleTangent = mFnCurve.tangent(5.0, OpenMaya.MSpace.kWorld)
    middleTangent.normalize()
    middleBinormal = middleTangent ^ middleNormal
    middleBinormal.normalize()

    print(middleNormal, middleTangent, middleBinormal)

    mselList = OpenMaya.MGlobal.getActiveSelectionList()
    mDagPath = mselList.getDagPath(0)

    transformation = OpenMaya.MMatrix(((middleTangent.x, middleTangent.y, middleTangent.z, 0.0),
                                      (middleNormal.x, middleNormal.y, middleNormal.z, 0.0),
                                      (middleBinormal.x, middleBinormal.y, middleBinormal.z, 0.0),
                                      (middlePoint.x, middlePoint.y, middlePoint.z, 1)))

    mfnTransform = OpenMaya.MFnTransform(mDagPath)
    mfnTransform.setTransformation(OpenMaya.MTransformationMatrix(transformation))



    """
    # rotate vector a over vector b
    quaternion = OpenMaya.MQuaternion(OpenMaya.MVector(1,0,0), middleTangent)

    mfnTransform = OpenMaya.MFnTransform(mDagPath)
    mfnTransform.setRotation(quaternion, 1)
    mfnTransform.setTranslation(OpenMaya.MVector(middlePoint), 4)
    """



def getdestination(element, attribute):
    mselList = OpenMaya.MSelectionList()
    mselList.add(element)
    meshObj = mselList.getDependNode(0)
    mfnShape = OpenMaya.MFnMesh(meshObj)
    mplug = mfnShape.findPlug(attribute, True)

    print mplug.name()
    print mplug.numChildren()
    print mplug.numConnectedChildren()
    print mplug.isConnected
    print mplug.numConnectedElements()
    print mplug.isElement
    print mplug.numElements()

    for i in range(mplug.evaluateNumElements()):
        mchild = mplug.elementByPhysicalIndex(i)
        print mchild.name()
        print mchild.numConnectedChildren()
        print mchild.isConnected
        print mchild.connectedTo(True, True)[0].name()
        print mchild.isElement


# getdestination(element='polySurfaceShape3', attribute='instObjGroups')