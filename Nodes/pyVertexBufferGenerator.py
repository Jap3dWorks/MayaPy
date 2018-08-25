# http://help.autodesk.com/view/MAYAUL/2016/ENU/?guid=__py_ref_scripted_2py_vertex_buffer_generator_8py_example_html

from ctypes import *
import maya.api.OpenMayaRender as OpenMayaRender
import maya.api.OpenMaya as OpenMaya

def maya_useNewAPI():
    """
    Tells maya it is build using Python API 2
    """
    pass

class MyCustomBufferGenerator(OpenMayaRender.MPxVertexBufferGenerator):
    def __init__(self):
        super(MyCustomBufferGenerator, self).__init__()

    def getSourceIndexing(self, object, sourceIndexing):
        # get the mesh from the object
        mesh = OpenMaya.MFnMesh(object)

        # if it is an empty mesh we do nothing
        numPolys = mesh.numPolygons
        if numPolys == 0:
            return False

        vertToFaceVertID = sourceIndexing.indices()
        faceNum = 0

        # for each face
        for i in range(0, numPolys):
            # assign a color ID to all vertices in this face
            faceColorID = faceNum % 3

            vertexCount = mesh.polygonVertexCount(i)
            for x in range(0, vertexCount):
                # set each face vertex to the face color
                vertToFaceVertID.append(faceColorID)

            faceNum += 1

        # assign the source indexing
        sourceIndexing.setComponentType(OpenMayaRender.MComponentDataIndexing.kFaceVertex)

        return False

    def getSourceStreams(self, object, sourceStreams):
        # no source streams needed
        return False


    def createVertexStream(self, object, vertexBuffer, targetIndexing, sharedIndexing, sourceStreams):
        # get the descriptor from the vertex buffer
        # it describes the format and layout of the stream
        descriptor = vertexBuffer.descriptor()

        # we are expecting a float stream
        if descriptor.dataType != OpenMayaRender.MGeometry.kFloat:
            return

        # we are expecting a float2
        if descriptor.dimetnsion != 2:
            return

        # we are expecting a texture channel
        if descriptor.semantic != OpenMayaRender.MGeometry.kTexture:
            return

        # get the mesh from the current path
        # if it is not a mesh we do nothing
        mesh = OpenMaya.MFnMesh(object)

        indices = targetIndexing.indices()

        vertexCount = len(indices)
        if vertexCount <= 0:
            return

        # fill the data
        buffer = vertexBuffer.acquire(vertexCount, True) # writeOnly = True - we don't need the current buffer values

        inc = sizeof(c_float)
        address = buffer

        for i in range(0, vertexCount):
            # Here we are embeding some custom data into the stream
            # The included effects (vertexBufferGeneratorGL.cgfx and
            # vertexBufferGeneratorDX11.fx)) will alternate
            # red, green, and blue vertex colored triangles based on this input.
            c_float.from_address(address).value = 1.0
            address += inc

            c_float.from_address(address).value = indices[i]  # color Index
            address += inc

        # commit the buffer to signal completion
        vertexBuffer.commit(buffer)

class MyCustomBufferGenerator2(OpenMayaRender.MPxVertexBufferGenerator):
    def __init__(self):
        super(MyCustomBufferGenerator2, self).__init__()

    def getSourceIndexing(self, object, sourceIndexing):
        # get the mesh from the object
        mesh = OpenMaya.MFnMesh(object)
        (vertexCount, vertexList) = mesh.getVertices()
        vertCount = len(vertexList)

        vertices = sourceIndexing.indices()
        for i in range(0, vertCount):
            vertices.append(vertexList[i])

        return True

    def getSourceStreams(self, object, sourceStreams):
        sourceStreams.append('Position')
        sourceStreams.append('Normal')
        return True

    def createVertexStream(self, object, vertexBuffer, targetIndexing, sharedIndexing, sourceStreams):
        # get the descriptor from the vertex buffer
        # It describes the format and layout of the stream
        descriptor = vertexBuffer.descriptor()

        # we are expecting a float or int stream
        dataType = descriptor.dataType
        if dataType != OpenMayaRender.MGeometry.kTexture and dataType != OpenMayaRender.MGeometry.kInt32:
            return

        # we are expecting a dimension of 3 or 4
        dimension = descriptor.dimension
        if dimension != 4 and dimension != 3:
            return

        # we are expecting a texture channel
        if descriptor.semantic != OpenMayaRender.MGeometry.kTexture:
            return

        # Get the mesh from the current path
        # if it is not a mesh we do nothing
        mesh = OpenMaya.MFnMesh(object)

        indices = targetIndexing.indices()
        vertexCount = len(indices)
        if vertexCount <= 0:
            return

        positionStream = sourceStreams.getBuffer('Position')
        if positionStream is None and positionStream.descriptor().dataType != OpenMayaRender.MGeometry.kFloat:
            return

        positionDimension = positionStream.descriptor().dimension
        if positionDimension != 3 and positionDimension != 4:
            return

        normalStream = sourceStreams.getBuffer('Normal')
        if normalStream is None or normalStream.descriptor().dataType != OpenMayaRender.MGeometry.kFloat:
            return
        normalDimension = normalStream.descriptor().dimension
        if normalDimension != 3 and normalDimension != 4:
            return

        # REVIEW this section, writing data
        positionBuffer = positionStream.map()
        if positionBuffer != 0:
            normalBuffer = normalStream.map()
            if normalBuffer != 0:
                compositeBuffer = vertexBuffer.aqcuire(vertexCount, True)  # writeOnly = True we don't need current values buffer
                if compositeBuffer != 0:

                    compaddress = compositeBuffer
                    posaddress = positionBuffer
                    normaddress = normalBuffer

                    floatinc = sizeof(c_float)
                    intinc = sizeof(c_int)

                    if dataType == OpenMayaRender.MGeometry.kFloat:
                        for i in range(0, vertexCount):
                            xcompaddr = compaddress
                            ycompaddr = compaddress+floatinc
                            zcompaddr = compaddress+floatinc*2
                            wcompaddr = compaddress+floatinc*3

                            #xposaddr = posaddress
                            yposaddr = posaddress+floatinc
                            zposaddr = posaddress+2*floatinc

                            xnormaddr = normaddress
                            #ynormaddr = normaddress + floatinc
                            znormaddr = normaddress+2*floatinc

                            c_float.from_address(xcompaddr).value = c_float.from_address(yposaddr).value  # store position.y
                            c_float.from_address(ycompaddr).value = c_float.from_address(zposaddr).value  # store position.z
                            c_float.from_address(zcompaddr).value = c_float.from_address(xnormaddr).value  # store normal.x

                            if dimension == 4:
                                c_float.from_address(wcompaddr).value = c_float.from_address(znormaddr).value  # store normal.z

                            compaddress += dimension*floatinc
                            posaddress += positionDimension*floatinc
                            normaddress += normalDimension*floatinc

                    elif dataType == OpenMayaRender.MGeometry.kInt32:
                        for i in range(0, vertexCount):
                            xcompaddr = compaddress
                            ycompaddr = compaddress+intinc
                            zcompaddr = compaddress+2*intinc
                            wcompaddr = compaddress+3*intinc

                            #xposaddr = posaddress
                            yposaddr = posaddress+floatinc
                            zposaddr = posaddress+2*floatinc

                            xnormaddr = normaddress
                            #ynormaddr = normaddress+floatinc
                            znormaddr = normaddress+2*floatinc

                            c_int.from_address(xcompaddr).value = c_float.from_address(yposaddr).value * 255  # store position.y
                            c_int.from_address(ycompaddr).value = c_float.from_address(zposaddr).value * 255  # store position.z
                            c_int.from_address(zcompaddr).value = c_float.from_address(xnormaddr).value * 255  # store normal.x
                            if dimension == 4:
                                c_int.from_address(wcompaddr).value = c_float.from_address(znormaddr).value * 255  # store normal.z

                            compaddress += dimension*intinc
                            posaddress += positionDimension*floatinc
                            normaddress += normalDimension*floatinc

                    vertexBuffer.commit(compositeBuffer)
                normalStream.unmap()
            positionStream.unmap()

# this is the buffer generator creation function registered with the draw
# Used to initialize the generator
def createMyCustomBufferGenerator():
    return MyCustomBufferGenerator()

def createMyCustomBufferGenerator2():
    return MyCustomBufferGenerator2()

def getCustomSemantics():
    if OpenMayaRender.drawAPI() == OpenMayaRender.MRenderer.kDirectX11:
        # register a generator based on a custom semantic for DX11.
        # You can use any name in DX11.
        return ('myCustomStream', 'muCustomStreamB')
    if OpenMayaRender.MRenderer.drawAPI() == OpenMayaRender.MRenderer.kOpenGLCoreProfile:
        # register a generator based on a custom semantic for OGSFX.
        # Pretty limited in OGSFX since it only allows standard semantics.
        # but thanks to the annotations a custom value can be set afterward from glslShader plugin
        return ('myCustomStream', 'myCustomStreamB')
    if OpenMayaRender.MRenderer.drawAPI() == OpenMayaRender.MRenderer.kOpenGL:
        # register a generator based on a custom semantic for cg.
        # Pretty limited in cg so we hook onto the ATTR semantics
        return ('ATTR8', 'ATTR7')

# the following routines are used to register/unregister
# the vertex generators with maya

def initializePlugin(obj):
    (customSemantic, customSemantic2) = getCustomSemantics()

    OpenMayaRender.MDrawRegistry.registerVertexBufferGenerator(customSemantic, createMyCustomBufferGenerator)
    OpenMayaRender.MDrawRegistry.registerVertexBufferGenerator(customSemantic2, createMyCustomBufferGenerator2)

def uninitialize(obj):
    (customSemantic, customSemantic2) = getCustomSemantics()

    OpenMayaRender.MDrawRegistry.deregisterVertexBufferGenerator(customSemantic)
    OpenMayaRender.MDrawRegistry.deregisterVertexBufferGenerator(customSemantic2)
