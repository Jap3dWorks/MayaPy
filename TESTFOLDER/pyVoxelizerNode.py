import sys
import maya.api.OpenMaya as OpenMaya


def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, objects created using the Maya Python API 2.0.
    """
    pass


# Plug-in information:
kPluginNodeName = 'voxelizerNode'  # The name of the node.
kPluginNodeId = OpenMaya.MTypeId(0xBEEF6)  # A unique ID associated to this node type.

# Default input values.
defaultVoxelWidth = 0.9  # The width of a cubic voxel.
defaultVoxelDistance = 1.0  # The distance which separates the center of two adjacent voxels.


##########################################################
# Plug-in
##########################################################
class VoxelizerNode(OpenMaya.MPxNode):
    # Static variables which will later be replaced by the node's attributes.
    voxelWidthAttribute = OpenMaya.MObject()
    voxelDistanceAttribute = OpenMaya.MObject()
    inputMeshAttribute = OpenMaya.MObject()
    outputMeshAttribute = OpenMaya.MObject()

    def __init__(self):
        ''' Constructor. '''
        # (!) Make sure you call the base class's constructor.
        OpenMaya.MPxNode.__init__(self)

    def compute(self, pPlug, pDataBlock):
        ''' Here, we will create a voxelized version of the input mesh. '''

        if (pPlug == VoxelizerNode.outputMeshAttribute):

            # Get our custom input node attributes and values.
            voxelWidthHandle = pDataBlock.inputValue(VoxelizerNode.voxelWidthAttribute)
            voxelWidth = voxelWidthHandle.asFloat()

            voxelDistanceHandle = pDataBlock.inputValue(VoxelizerNode.voxelDistanceAttribute)
            voxelDistance = voxelDistanceHandle.asFloat()

            inputMeshHandle = pDataBlock.inputValue(VoxelizerNode.inputMeshAttribute)
            inputMeshObj = inputMeshHandle.asMesh()

            # Compute the bounding box around the mesh vertices.
            boundingBox = self.getBoundingBox(inputMeshObj)

            # Determine which voxel centerpoints are contained within the mesh.
            voxels = self.getVoxels(voxelDistance, inputMeshObj, boundingBox)

            # Create a mesh data container, which will store our new voxelized mesh.
            meshDataFn = OpenMaya.MFnMeshData()
            newOutputMeshData = meshDataFn.create()

            # Create a cubic polygon for each voxel and populate the 'newOutputMeshData' MeshData object.
            self.createVoxelMesh(voxels, voxelWidth, newOutputMeshData)

            # Set the output data.
            outputMeshHandle = pDataBlock.outputValue(VoxelizerNode.outputMeshAttribute)
            outputMeshHandle.setMObject(newOutputMeshData)

        else:
            return OpenMaya.kUnknownParameter

    def getBoundingBox(self, pMeshObj):
        ''' Calculate a bounding box around the mesh vertices. '''

        # Create the bounding box object we will populate with the points of the mesh.
        boundingBox = OpenMaya.MBoundingBox()

        meshFn = OpenMaya.MFnMesh(pMeshObj)

        pointArray = OpenMaya.MPointArray()

        # Get the points of the mesh in its local coordinate space.
        pointArray = meshFn.getPoints(OpenMaya.MSpace.kTransform)

        for i in range(0, len(pointArray)):
            point = pointArray[i]
            boundingBox.expand(point)

        return boundingBox

    def getVoxels(self, pVoxelDistance, pMeshObj, pBoundingBox):
        '''
        Obtain a list of voxels as a set of (x,y,z) coordinates in the mesh local space.

        We obtain these voxels by casting rays from points separated pVoxelDistance apart within the
        mesh bounding box, and test whether or not these points are contained within the mesh.

        A point is contained within a closed mesh if the ray shot from the point intersects an odd
        number of times with the surface of the mesh.
        '''
        # Initialize a list of voxels contained within the mesh.
        voxels = []

        # Get a reference to the MFnMesh function set, and use it on the given mesh object.
        meshFn = OpenMaya.MFnMesh(pMeshObj)

        # Compute an offset which we will apply to the min and max corners of the bounding box.
        halfVoxelDist = 0.5 * pVoxelDistance

        # Offset the position of the minimum point to account for the inter-voxel distance.
        minPoint = pBoundingBox.min
        minPoint.x += halfVoxelDist
        minPoint.y += halfVoxelDist
        minPoint.z += halfVoxelDist

        # Offset the position of the maximum point to account for the inter-voxel distance.
        maxPoint = pBoundingBox.max
        maxPoint.x += halfVoxelDist
        maxPoint.y += halfVoxelDist
        maxPoint.z += halfVoxelDist

        # Define an iterator which will allow us to step through the pVoxelDistance
        # point intervals contained within our bounding box. We use this iterator
        # in the for loops that follow to visit each voxel center in the bounding box.
        def floatIterator(start, stop, step):
            r = start
            while r < stop:
                yield r
                r += step

        # Iterate over every point in the bounding box, stepping by pVoxelDistance...
        for xCoord in floatIterator(minPoint.x, maxPoint.x, pVoxelDistance):
            for yCoord in floatIterator(minPoint.y, maxPoint.y, pVoxelDistance):
                for zCoord in floatIterator(minPoint.z, maxPoint.z, pVoxelDistance):

                    # 2D representation of a ray cast from the point within the bounding box:
                    #
                    #  (+) ^-----------------
                    #      |                |
                    #  y   |                |  - We are shooting the ray from the point: [*]
                    # axis | <======[*]     |  - The direction of the ray is parallel to the -Z axis.
                    #      |                |
                    #      |                |
                    #  (-) ------------------>
                    #     (-)    z axis     (+)
                    #
                    # If the ray intersects with an odd number of points along the surface of the mesh, the
                    # point is contained within the mesh (assuming a closed mesh).
                    raySource = OpenMaya.MFloatPoint(xCoord, yCoord, zCoord)
                    rayDirection = OpenMaya.MFloatVector(0, 0, -1)
                    # intersectionPoints = OpenMaya.MFloatPointArray()
                    tolerance = 0.0001

                    ret = meshFn.allIntersections(raySource,  # raySource - where we are shooting the ray from.
                                                  rayDirection,
                                                  # rayDirection - the direction in which we are shooting the ray.
                                                  OpenMaya.MSpace.kTransform,
                                                  # coordinate space - the mesh's local coordinate space.
                                                  float(9999),  # maxParam - the range of the ray.
                                                  False,
                                                  # testBothDirections - we are not checking both directions from the raySource
                                                  tolerance=tolerance,
                                                  # tolerance - a numeric tolerance threshold which allow intersections to occur just outside the mesh.
                                                  )

                    # Returns a tuple of:
                    # -> (hitPoints, hitRayParams, hitFaces, hitTriangles, hitBary1s, hitBary2s)

                    # If there is an odd number of intersection points, then the point lies within the mesh. Otherwise,
                    # the point lies outside the mesh. We are only concerned with voxels whose centerpoint lies within the mesh
                    if (len(ret[0]) % 2 == 1):
                        voxels.append(raySource)

        # Return the list of voxel coordinates which lie within the mesh.
        return voxels

    def createVoxelMesh(self, pVoxelPositions, pVoxelWidth, pOutMeshData):
        ''' Create a mesh containing one cubic polygon for each voxel in the pVoxelPositions list. '''

        numVoxels = len(pVoxelPositions)

        numVerticesPerVoxel = 8  # a cube has eight vertices.
        numPolygonsPerVoxel = 6  # a cube has six faces.
        numVerticesPerPolygon = 4  # four vertices are required to define a face of a cube.
        numPolygonConnectsPerVoxel = numPolygonsPerVoxel * numVerticesPerPolygon  # 24

        # Initialize the required arrays used to create the mesh in MFnMesh.create()
        totalVertices = numVoxels * numVerticesPerVoxel
        vertexArray = OpenMaya.MFloatPointArray()
        vertexArray.setLength(totalVertices)
        vertexIndexOffset = 0

        totalPolygons = numVoxels * numPolygonsPerVoxel
        polygonCounts = OpenMaya.MIntArray()
        polygonCounts.setLength(totalPolygons)
        polygonCountsIndexOffset = 0

        totalPolygonConnects = numVoxels * numPolygonConnectsPerVoxel
        polygonConnects = OpenMaya.MIntArray()
        polygonConnects.setLength(totalPolygonConnects)
        polygonConnectsIndexOffset = 0

        # Populate the required arrays used in MFnMesh.create()
        for i in range(0, numVoxels):
            voxelPosition = pVoxelPositions[i]

            # Add a new cube to the arrays.
            self.createCube(voxelPosition, pVoxelWidth,
                            vertexArray, vertexIndexOffset, numVerticesPerVoxel,
                            polygonCounts, polygonCountsIndexOffset, numPolygonsPerVoxel, numVerticesPerPolygon,
                            polygonConnects, polygonConnectsIndexOffset)

            # Increment the respective index offsets.
            vertexIndexOffset += numVerticesPerVoxel
            polygonCountsIndexOffset += numPolygonsPerVoxel
            polygonConnectsIndexOffset += numPolygonConnectsPerVoxel

        # Create the mesh now that the arrays have been populated. The mesh is stored in pOutMeshData
        meshFn = OpenMaya.MFnMesh()
        meshFn.create(vertexArray, polygonCounts, polygonConnects, parent=pOutMeshData)

    def createCube(self, pVoxelPosition, pWidth,
                   pVertexArray, pVertexIndexOffset, pNumVerticesPerVoxel,
                   pPolygonCountArray, pPolygonCountIndexOffset, pNumPolygonsPerVoxel, pNumVerticesPerPolygon,
                   pPolygonConnectsArray, pPolygonConnectsIndexOffset):
        ''' Add a cubic polygon to the specified arrays. '''

        # We are using half the given width to compute the vertices of the cube.
        halfWidth = float(pWidth / 2.0)

        # Declare the eight corners of the cube. The cube is centered at pVoxelPosition.

        vertices = [OpenMaya.MFloatPoint(-halfWidth + pVoxelPosition.x, -halfWidth + pVoxelPosition.y,
                                         -halfWidth + pVoxelPosition.z),  # 0
                    OpenMaya.MFloatPoint(halfWidth + pVoxelPosition.x, -halfWidth + pVoxelPosition.y,
                                         -halfWidth + pVoxelPosition.z),  # 1
                    OpenMaya.MFloatPoint(halfWidth + pVoxelPosition.x, -halfWidth + pVoxelPosition.y,
                                         halfWidth + pVoxelPosition.z),  # 2
                    OpenMaya.MFloatPoint(-halfWidth + pVoxelPosition.x, -halfWidth + pVoxelPosition.y,
                                         halfWidth + pVoxelPosition.z),  # 3
                    OpenMaya.MFloatPoint(-halfWidth + pVoxelPosition.x, halfWidth + pVoxelPosition.y,
                                         -halfWidth + pVoxelPosition.z),  # 4
                    OpenMaya.MFloatPoint(-halfWidth + pVoxelPosition.x, halfWidth + pVoxelPosition.y,
                                         halfWidth + pVoxelPosition.z),  # 5
                    OpenMaya.MFloatPoint(halfWidth + pVoxelPosition.x, halfWidth + pVoxelPosition.y,
                                         halfWidth + pVoxelPosition.z),  # 6
                    OpenMaya.MFloatPoint(halfWidth + pVoxelPosition.x, halfWidth + pVoxelPosition.y,
                                         -halfWidth + pVoxelPosition.z)]  # 7

        # Declare the data structure which binds each vertex to a polygon corner
        polygonConnections = [(0, 12, 16),
                              # the vertex indexed at 0 corresponds to the polygon corners whose indexes are (0, 12, 16) in pPolygonConnectsArray.
                              (1, 19, 20),
                              (2, 9, 23),
                              (3, 8, 13),
                              (4, 15, 17),
                              (5, 11, 14),
                              (6, 10, 22),
                              (7, 18, 21)]

        # Store the eight corners of the cube in the vertex array.
        for i in range(0, pNumVerticesPerVoxel):
            # Store the vertex in the passed vertex array.
            pVertexArray[pVertexIndexOffset + i] = vertices[i]

            # Assign the vertex in the pVertexArray to the relevant polygons.
            for polygonConnectionIndex in polygonConnections[i]:
                pPolygonConnectsArray[pPolygonConnectsIndexOffset + polygonConnectionIndex] = pVertexIndexOffset + i

        # Declare the number of vertices for each face.
        for i in range(0, pNumPolygonsPerVoxel):
            # Set the number of vertices for the polygon at the given index.
            pPolygonCountArray[pPolygonCountIndexOffset + i] = pNumVerticesPerPolygon


##########################################################
# Plug-in initialization.
##########################################################
def nodeCreator():
    ''' Creates an instance of our node class and delivers it to Maya as a pointer. '''
    return VoxelizerNode()


def nodeInitializer():
    ''' Defines the input and output attributes as static variables in our plug-in class. '''
    # The following MFnNumericAttribute function set will allow us to create our attributes.
    numericAttributeFn = OpenMaya.MFnNumericAttribute()

    # This one allows us to create our input and output mesh attributes.
    typedAttributeFn = OpenMaya.MFnTypedAttribute()

    # ==================================
    # INPUT NODE ATTRIBUTE(S)
    # ==================================
    # We will need a voxel width.
    global defaultVoxelWidth
    VoxelizerNode.voxelWidthAttribute = numericAttributeFn.create('voxelWidth', 'vw',
                                                                  OpenMaya.MFnNumericData.kFloat, defaultVoxelWidth)
    numericAttributeFn.writable = True
    numericAttributeFn.readable = False
    numericAttributeFn.storable = True
    numericAttributeFn.hidden = False
    numericAttributeFn.setMin(0.1)
    VoxelizerNode.addAttribute(VoxelizerNode.voxelWidthAttribute)

    # We will need a voxel distance value (higher values means we can see more voxels within the volume of the mesh).
    global defaultVoxelDistance
    VoxelizerNode.voxelDistanceAttribute = numericAttributeFn.create('voxelDistance', 'vd',
                                                                     OpenMaya.MFnNumericData.kFloat,
                                                                     defaultVoxelDistance)
    numericAttributeFn.writable = True
    numericAttributeFn.readable = False
    numericAttributeFn.storable = True
    numericAttributeFn.hidden = False
    numericAttributeFn.setMin(0.1)
    VoxelizerNode.addAttribute(VoxelizerNode.voxelDistanceAttribute)

    # We will need an input mesh attribute.
    VoxelizerNode.inputMeshAttribute = typedAttributeFn.create('inputMesh', 'im',
                                                               OpenMaya.MFnData.kMesh)
    typedAttributeFn.writable = True
    typedAttributeFn.readable = False
    typedAttributeFn.storable = False
    typedAttributeFn.hidden = False
    VoxelizerNode.addAttribute(VoxelizerNode.inputMeshAttribute)

    # ==================================
    # OUTPUT NODE ATTRIBUTE(S)
    # ==================================
    VoxelizerNode.outputMeshAttribute = typedAttributeFn.create('outputMesh', 'om',
                                                                OpenMaya.MFnData.kMesh)
    typedAttributeFn.writable = False
    typedAttributeFn.readable = True
    typedAttributeFn.storable = False
    typedAttributeFn.hidden = False
    VoxelizerNode.addAttribute(VoxelizerNode.outputMeshAttribute)

    # ==================================
    # NODE ATTRIBUTE DEPENDENCIES
    # ==================================
    # If any of the inputs change, the output mesh will be recomputed.
    VoxelizerNode.attributeAffects(VoxelizerNode.voxelWidthAttribute, VoxelizerNode.outputMeshAttribute)
    VoxelizerNode.attributeAffects(VoxelizerNode.voxelDistanceAttribute, VoxelizerNode.outputMeshAttribute)
    VoxelizerNode.attributeAffects(VoxelizerNode.inputMeshAttribute, VoxelizerNode.outputMeshAttribute)


def initializePlugin(mobject):
    ''' Initialize the plug-in '''
    mplugin = OpenMaya.MFnPlugin(mobject)
    try:
        mplugin.registerNode(kPluginNodeName, kPluginNodeId, nodeCreator, nodeInitializer)
    except:
        sys.stderr.write('Failed to register node: ' + kPluginNodeName)
        raise


def uninitializePlugin(mobject):
    ''' Uninitializes the plug-in '''
    mplugin = OpenMaya.MFnPlugin(mobject)
    try:
        mplugin.deregisterNode(kPluginNodeId)
    except:
        sys.stderr.write('Failed to deregister node: ' + kPluginNodeName)
        raise


''' 
# Copy the following lines and run them in Maya's Python Script Editor:

import maya.cmds as cmds

cmds.file( newFile=True, force=True )

cmds.unloadPlugin( 'pyVoxelizerNode.py' )
cmds.loadPlugin( 'pyVoxelizerNode.py' )

# Create a sphere which will act as our input shape.
cmds.polySphere( r=5.0, sx=20, sy=20, name='sphere1' )
cmds.move( -20, 0, 0, 'sphere1' ) # move it over to the side.

# Create the voxelization node.
cmds.createNode( 'voxelizerNode', name='voxelizerNode1' )

# Create a target shape.
cmds.createNode( 'transform', name='target1' )
cmds.createNode( 'mesh', name='target1Shape', parent='target1' )
cmds.sets( 'target1Shape', add='initialShadingGroup' )

# Connect the attributes.
cmds.connectAttr( 'sphere1Shape.outMesh', 'voxelizerNode1.inputMesh' )
cmds.connectAttr( 'voxelizerNode1.outputMesh', 'target1Shape.inMesh' )

'''