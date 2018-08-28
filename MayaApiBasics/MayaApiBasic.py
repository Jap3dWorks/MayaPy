# this script act over polyCubes Primitives, change subdivisions.
# here we are going to act over MDagPath, MObject and Plugs.
import maya.api.OpenMaya as OpenMaya

# TODO: it is too slow. 
def APITEST(arg=10):
    mSel = OpenMaya.MSelectionList()
    mSel.merge(OpenMaya.MGlobal.getActiveSelectionList())

    mSelIt = OpenMaya.MItSelectionList(mSel, OpenMaya.MFn.kTransform)
    # this is the way for itterating on MSelectionList While not var.isDone() and var.next()
    while not mSelIt.isDone():
        transform = mSelIt.getDagPath()
        mfnTransform = OpenMaya.MFnTransform(transform)
        
        # get shape as a dagPath Object
        shape = transform.extendToShape()
        
        # get mobject of shape
        shapeObject = shape.node()
        # check type of mObject
        print ('\n===========================================================\n')
        print ('%s is MObject type: %s' % (shape, shape.node().apiTypeStr))

        # get connections, first we need a maya function class
        # which let us operate on maya api objects.
        # in this case, we are operating on a mesh so we need MFnMesh
        mFnMesh = OpenMaya.MFnMesh(shape)
        # with MFnMesh we can get an array of plugs
        mPlugArray = mFnMesh.getConnections()  # mplugArray Class
        
        for i in range(len(mPlugArray)):
            print ('%s plugs are: %s' % (shape, mPlugArray[i]))
        
        # we need the second plug of the array,
        # and use another MPlugArray to store on which plugs are connected
        mPlugArray_connections = mPlugArray[1].connectedTo(True, False)
        # print all the found plugs
        for i in range(len(mPlugArray_connections)):
            print ('%s plug %s is connected to: %s' % (shape, mPlugArray[1], mPlugArray_connections[i]))
            
        # once we have our mplugArray of polyCube. we can find the polyCube node
        cubeNode = mPlugArray_connections[0].node()  # node as an mObject
        cubeNodeFn = OpenMaya.MFnDependencyNode(cubeNode)  # MFn to operate over dependenvy Graph nodes
        
        # print cubeNodeFn.getAliasList()  # this method doen't is giving anything
        
        #  we are to iterating over the attributes, and when we find the desired attribute, edit it.
        for i in range(cubeNodeFn.attributeCount()):
            # get the name of the attribute
            # in findPlug, i need to give a MObject with the plug
            # .attribute => MObject (attribute)
            # .attribute give us the index attribute as a MObject
            cubeNodeAttr = cubeNodeFn.attribute(i)
            print 'plug is type: %s' % cubeNodeAttr.apiTypeStr
            cubeNodePlug = cubeNodeFn.findPlug(cubeNodeAttr , True)
            print (cubeNodePlug.info)  # names of the attributes
            if cubeNodePlug.info == '%s.subdivisionsHeight' %cubeNodeFn.name():
                # to operate over an attribute, we need a plug. It give us the methods for that pourpose 
                cubeNodePlug.setInt(arg)
            
            cubeNodeAttr = None
            cubeNodePlug = None
        # next item in the MArray
        mSelIt.next()

if __name__=='__main__':
    APITEST(2)