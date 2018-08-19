# https://help.autodesk.com/view/MAYAUL/2018/ENU/?guid=__py_ref_scripted_2py_draw_foot_printby_render_utilities_8py_example_html
# https://knowledge.autodesk.com/support/maya/learn-explore/caas/CloudHelp/cloudhelp/2018/ENU/Maya-SDK/files/GUID-66E42F2E-DB0D-44EF-B4DA-7F43D155692A-htm.html

import ctypes
import sys
import maya.api.OpenMayaUI as OpenMayaUI
import maya.api.OpenMaya as OpenMaya
import maya.api.OpenMayaRender as OpenMayaRender
import maya.api.OpenMayaAnim as OpenMayaAnim
import maya.OpenMayaRender as OpenMayaRender1

def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, objects created using the Maya Python API 2.0.
    """
    pass

def matrixAsArray(matrix):
    array = []
    for i in range(16):
        array.append(matrix[i])
        return array

# foot data, this is interesting
# because we can for example use json files to store different shapes.
# TODO try saving point in json files and then change the locator shape
sole = [ [  0.00, 0.0, -0.70 ],
        [  0.04, 0.0, -0.69 ],
        [  0.09, 0.0, -0.65 ],
        [  0.13, 0.0, -0.61 ],
        [  0.16, 0.0, -0.54 ],
        [  0.17, 0.0, -0.46 ],
        [  0.17, 0.0, -0.35 ],
        [  0.16, 0.0, -0.25 ],
        [  0.15, 0.0, -0.14 ],
        [  0.13, 0.0,  0.00 ],
        [  0.00, 0.0,  0.00 ],
        [ -0.13, 0.0,  0.00 ],
        [ -0.15, 0.0, -0.14 ],
        [ -0.16, 0.0, -0.25 ],
        [ -0.17, 0.0, -0.35 ],
        [ -0.17, 0.0, -0.46 ],
        [ -0.16, 0.0, -0.54 ],
        [ -0.13, 0.0, -0.61 ],
        [ -0.09, 0.0, -0.65 ],
        [ -0.04, 0.0, -0.69 ],
        [ -0.00, 0.0, -0.70 ] ]
heel = [ [  0.00, 0.0,  0.06 ],
        [  0.13, 0.0,  0.06 ],
        [  0.14, 0.0,  0.15 ],
        [  0.14, 0.0,  0.21 ],
        [  0.13, 0.0,  0.25 ],
        [  0.11, 0.0,  0.28 ],
        [  0.09, 0.0,  0.29 ],
        [  0.04, 0.0,  0.30 ],
        [  0.00, 0.0,  0.30 ],
        [ -0.04, 0.0,  0.30 ],
        [ -0.09, 0.0,  0.29 ],
        [ -0.11, 0.0,  0.28 ],
        [ -0.13, 0.0,  0.25 ],
        [ -0.14, 0.0,  0.21 ],
        [ -0.14, 0.0,  0.15 ],
        [ -0.13, 0.0,  0.06 ],
        [ -0.00, 0.0,  0.06 ] ]
soleCount = 21
heelCount = 17

##############################################
# node implementation with standard viewport #
##############################################
class footPrint(OpenMayaUI.MPxLocatorNode):
    # info of the node
    id = OpenMaya.MTypeId(0x80007)
    drawDbClassification = 'drawdb/geometry/footPrint'
    drawRegistrantId = 'FootprintNodePlugin'

    # size of the foot
    size = None

    @staticmethod
    def creator():
        return footPrint()

    @staticmethod
    def initialize():
        # MFnUnitAttribute Function set for creating and working with angle, distance and time attributes
        # in this case we want to work with distance.
        unitFn = OpenMaya.MFnUnitAttribute()

        footPrint.size = unitFn.create('size', 'sz', OpenMaya.MFnUnitAttribute.kDistance)
        unitFn.default = OpenMaya.MDistance(1.0)

        # add new attributes, this method can only be launched on the static initialize
        OpenMaya.MPxNode.addAttribute(footPrint.size)

    def __init__(self):
        super(footPrint, self).__init__()

    def compute(self, plug, dataBlock):
        return None

    def draw(self, view, path, style, status):
        # get the size
        # thisMObject Returns the MObject associated with this user defined node.
        # This makes it possible to use MFnDependencyNode or to construct plugs to this node's attributes.
        thisNode = self.thisMObject()
        plug = OpenMaya.MPlug(thisNode, footPrint.size)
        sizeVal = plug.asMDistance()
        multiplier = sizeVal.asCentimeters()

        # declare global variables
        global sole, soleCount
        global heel, heelCount

        # beginGl and endGL tells maya that we are going to use OpenGL commands between them.
        view.beginGL()

        # drawing in VP1 will be done using V1 pythons API
        glRenderer = OpenMayaRender1.MHardwareRenderer.theRenderer()
        glFT = glRenderer.glFunctionTable()

        if (style == OpenMayaUI.M3dView.kFlatShaded) or (style == OpenMayaUI.M3dView.kGouraudShaded):
            # pushed current state. glPushAttrib take a mask
            # that indicates which group of states variables save on the attribute stack.
            # GL_CURRENT_BIT current RGBA color
            # MGL_ refer OpenGL (GL_) functions in maya. maya has it's oun implementation.
            glFT.glPushAttrib(OpenMayaRender1.MGL_CURRENT_BIT)

            # Show both faces
            glFT.glDisable(OpenMayaRender1.MGL_CULL_FACE)

            if status == OpenMayaUI.M3dView.kActive:
                # by index color in this case 13, the the color overdraw
                view.setDrawColor(13, OpenMayaUI.M3dView.kActiveColors)
            else:
                view.setDrawColor(13, OpenMayaUI.M3dView.kDormantColors)

            """
            ### another method to colorize ###
            # enable blend mode, to enable transparency
            glFT.glEnable(OpenMayaRender.MGL_BLEND)
            # defined blend function
            glFT.glBlendFunc(OpenMayaRender.MGL_SRC_ALPHA, OpenMayaRender.MGL_ONE_MINUS_SRC_ALPHA)
    
            # Define Colors for different selection modes
            # glColor4f is the function to change color, glColor3f if we do not want edit alpha
            if status == view.kActive:
                glFT.glColor4f(0.2,0.5,0.1,0.3)
            elif status == view.kLead:
                glFT.glColor4f(0.5,0.2,0.1,0.3)
            elif status == view.kDormant:
                glFT.glColor4f(0.1,0.1,0.1,0.3)
            """

            # Draw a shape.
            # glBegin allow us to enter in primitive draw mode.
            # glEnd shut down communication with graphic card and return to the main program.
            glFT.glBegin(OpenMayaRender1.MGL_TRIANGLE_FAN)
            # define points.
            for i in range(soleCount-1):
                glFT.glVertex3f(sole[i][0]*multiplier, sole[i][1]*multiplier, sole[i][2]*multiplier)
            # end communication with graphic card
            glFT.glEnd()

            glFT.glBegin(OpenMayaRender1.MGL_TRIANGLE_FAN)
            for i in range(heelCount-1):
                glFT.glVertex3f(heel[i][0]*multiplier, heel[i][1]*multiplier, heel[i][2]*multiplier)
            glFT.glEnd()

            # glPopAttrib() restores the values of the state variables saved with the last glPushAttrib command.
            # Those not saved are left unchanged.
            glFT.glPopAttrib()

        # Draw the outline of the foot
        glFT.glBegin(OpenMayaRender1.MGL_LINES)
        for i in range(soleCount-1):
            glFT.glVertex3f(sole[i][0]*multiplier, sole[i][1]*multiplier, sole[i][2]*multiplier)
            glFT.glVertex3f(sole[i+1][0]*multiplier, sole[i+1][1]*multiplier, sole[i+1][2]*multiplier)

        for i in range(heelCount-1):
            glFT.glVertex3f(heel[i][0] * multiplier, heel[i][1] * multiplier, heel[i][2] * multiplier)
            glFT.glVertex3f(heel[i + 1][0] * multiplier, heel[i + 1][1] * multiplier, heel[i + 1][2] * multiplier)
        glFT.glEnd()

        view.endGL()

        # Draw name of the footprint
        view.setDrawColor(OpenMaya.MColor((0.1, 0.8, 0.8, 1.0)))
        view.drawText('FootPrint', OpenMaya.MPoint(0,0,0), OpenMayaUI.M3dView.kCenter)

    def isBounded(self):
        return True

    def boundingBox(self):
        # Get the size
        # thisObject Returns the MObject associated with this user defined node.
        # This makes it possible to use MFnDependencyNode or to construct plugs to this node's attributes.
        thisNode = self.thisMObject()
        plug = OpenMaya.MPlug(thisNode, footPrint.size)
        sizeVal = plug.asMDistance()
        multiplier = sizeVal.asCentimeters()

        corner1 = OpenMaya.MPoint(-0.17, 0.0, -0.7)
        corner2 = OpenMaya.MPoint(0.17, 0.0, 0.3)

        # multiply corner values per footPrint.size attribute
        corner1 *= multiplier
        corner2 *= multiplier

        return OpenMaya.MBoundingBox(corner1, corner2)

#################################
# Maya viewport2 implementation #
#################################
# MUserData Virtual base class for user data caching.
class footPrintData(OpenMaya.MUserData):
    def __init__(self):
        OpenMaya.MUserData.__init__(self, False)  # don't delete after draw

        self.fMultiplier = 0.0
        self.fColor = [0.0, 0.0, 0.0]
        self.fCustomBoxDraw = False  # REVIEW: default value is False
        # MDAGDrawOverrideInfo() a data structure to store the per path draw override information
        # normal, reference, template, ...
        self.fDrawOV = OpenMaya.MDAGDrawOverrideInfo()

# helper class declaration for the object drawing
class footPrintDrawAgent:
    def __init__(self):
        self.mShader = None

        self.mBoundingBoxVertexBuffer = None
        self.mBoundingBoxIndexBuffer = None
        self.mSoleVertexBuffer = None
        self.mHeelVertexBuffer = None
        self.mSoleWireIndexBuffer = None
        self.mHeelWireIndexBuffer = None
        self.mSoleShadedIndexBuffer = None
        self.mHeelShadedIndexBuffer = None

    def __del__(self):
        if self.mShader is not None:
            # MRenderer Main interface class to the Viewport 2.0 renderer
            # getShaderManager() Returns the shader manager or None
            # if the renderer is not initialized properly.
            shaderMgr = OpenMayaRender.MRenderer.getShaderManager()
            if shaderMgr is not None:
                # MShaderManager.releaseShader() should be called to notify the shader manager
                # that the caller is done with the shader
                shaderMgr.releaseShader(self.mShader)
            self.mShader = None

        self.mBoundingBoxVertexBuffer = None
        self.mBoundingBoxIndexBuffer = None
        self.mSoleVertexBuffer = None
        self.mHeelVertexBuffer = None
        self.mSoleWireIndexBuffer = None
        self.mHeelWireIndexBuffer = None
        self.mHeelShadedIndexBuffer = None

    def beginDraw(self, context, color, scale):
        self.initShader()
        self.initBuffers()

        if self.mShader is not None:
            self.mShader.setParameter('matColor', color)
            self.mShader.setParameter('scale', scale)
            self.mShader.bind(context)
            self.mShader.activatePass(context, 0)

    def drawShaded(self, context):
        global soleCount, heelCount
        # context (MDrawContext) - The draw context to use for render.
        # Draw the sole
        # http://help.autodesk.com/view/MAYAUL/2016/ENU/?guid=__py_ref_class_open_maya_render_1_1_m_render_utilities_html

        if self.mSoleVertexBuffer is not None and self.mSoleWireIndexBuffer is not None:
            OpenMayaRender.MRenderUtilities.drawSimpleMesh(context, self.mSoleVertexBuffer,
                                                           self.mSoleWireIndexBuffer, OpenMayaRender.MGeometry.kLines,
                                                           0, 2 * (soleCount-1))

        # Draw the heel
        if self.mHeelVertexBuffer is not None and self.mHeelWireIndexBuffer is not None:
            OpenMayaRender.MRenderUtilities.drawSimpleMesh(context, self.mHeelVertexBuffer,
                                                           self.mHeelWireIndexBuffer, OpenMayaRender.MGeometry.kLines,
                                                           0, 2 * (heelCount-1))

    def drawBoundingBox(self, context):
        if self.mBoundingBoxVertexBuffer is not None and self.mBoundingBoxIndexBuffer is not None:
            OpenMayaRender.MRenderUtilities.drawSimpleMesh(context, self.mBoundingBoxVertexBuffer, self.mBoundingBoxIndexBuffer, OpenMayaRender.MGeometry.kLines, 0, 24)

    def drawWireFrame(self, context):
        global soleCount, heelCount

        # draw the sole
        if self.mSoleVertexBuffer is not None and self.mSoleWireIndexBuffer is not None:
            OpenMayaRender.MRenderUtilities.drawSimpleMesh(context, self.mSoleVertexBuffer, self.mSoleWireIndexBuffer, OpenMayaRender.MGeometry.kLines, 0, 2*(soleCount-1))

        # draw the heel
        if self.mHeelVertexBuffer is not None and self.mHeelWireIndexBuffer is not None:
            OpenMayaRender.MRenderUtilities.drawSimpleMesh(context, self.mHeelVertexBuffer, self.mHeelWireIndexBuffer, OpenMayaRender.MGeometry.kLines, 0, 2*(heelCount-1))

    def endDraw(self, context):
        if self.mShader is not None:
            self.mShader.unbind(context)

    def initShader(self):
        if self.mShader is None:
            shaderMgr = OpenMayaRender.MRenderer.getShaderManager()
            if shaderMgr is not None:
                shaderCode = self.getShaderCode()
                self.mShader = shaderMgr.getEffectsBufferShader(shaderCode, len(shaderCode), '')
        # return True or False
        return self.mShader is not None

    def shaderCode(self):
        return ''

    def initBuffers(self):
        global soleCount, sole
        global heelCount, heel

        #EXPLANATION: VERTEX BUFFERS and INDEX BUFFERS Maya API:
        # https://knowledge.autodesk.com/support/maya/learn-explore/caas/CloudHelp/cloudhelp/2018/ENU/Maya-SDK/files/GUID-148A1EF1-B350-416F-A800-C47DA90D1369-htm.html
        if self.mBoundingBoxVertexBuffer is None:
            count = 8
            rawData = [[ -0.5, -0.5, -0.5 ],
                       [  0.5, -0.5, -0.5 ],
                       [  0.5, -0.5,  0.5 ],
                       [ -0.5, -0.5,  0.5 ],
                       [ -0.5,  0.5, -0.5 ],
                       [  0.5,  0.5, -0.5 ],
                       [  0.5,  0.5,  0.5 ],
                       [ -0.5,  0.5,  0.5 ]]

            desc = OpenMayaRender.MVertexBufferDescriptor('', OpenMayaRender.MGeometry.kPosition, OpenMayaRender.MGeometry.kFloat, 3)
            self.mBoundingBoxVertexBuffer = OpenMayaRender.MVertexBuffer(desc)

            dataAddress = self.mBoundingBoxVertexBuffer.acquire(count, True)
            # is a foreign function library for Python.
            # It provides C compatible data types, and allows calling functions in DLLs or shared libraries.
            # It can be used to wrap these libraries in pure Python.
            data = ((ctypes.c_float*3)*count).from_address(dataAddress)

            for i in range(count):
                data[i][0] = rawData[i][0]
                data[i][1] = rawData[i][1]
                data[i][2] = rawData[i][2]

            self.mBoundingBoxVertexBuffer.commit(dataAddress)
            dataAddress = None
            data = None

        if self.mBoundingBoxIndexBuffer is None:
            count = 24
            rawData = [0,1,
                       1,2,
                       2,3,
                       3,0,
                       4,5,
                       5,6,
                       6,7,
                       7,4,
                       0,4,
                       1,5,
                       2,6,
                       3,7]

            # buffers EXPLANATION // explain better rawData // raw data is an indexBuffer
            # here we get a space in memory and the fill it with C Data types
            # https://vulkan-tutorial.com/Vertex_buffers/Index_buffer  <-- indexBuffer EXPLANATION

            # the indices need to be uploaded to ha vkBuffer for the GPU be able to them
            # MIndexBuffer represents an index buffer with a specific data. usable with MGeometry
            self.mBoundingBoxIndexBuffer = OpenMayaRender.MIndexBuffer(OpenMayaRender.MGeometry.kUnsignedInt32)

            # acquire() may be called to get a pointer to a block of memory to fill with said data.
            # args: size of the buffer(int) // writeOnly (bool)

            # Once filled, commit() must be called to apply the data to the buffer.
            dataAddress = self.mBoundingBoxIndexBuffer.acquire(count, True)
            # ctypes provides C compatible data types, and allows calling functions in DLLs or shared libraries.
            # It can be used to wrap these libraries in pure Python.

            # http://pyplusplus.readthedocs.io/en/latest/tutorials/functions/transformation/from_address.html  <-- from_address EXPLANATION
            # unsigned_int * count -> [c_uint][c_uint]... count times
            # from_address you can use ctypes package to create the data and than pass it to
            # the Boost.Python exposed function, in this case dataAddress
            data = (ctypes.c_uint * count).from_address(dataAddress)

            # fill our buffer
            for i in range(count):
                data[i] = rawData[i]

            # here is the commit(), once we filled dataAddress with c types through .from_address from data.
            # Commit the data stored in the memory given by acquire() to the buffer.
            self.mBoundingBoxIndexBuffer.commit(dataAddress)
            dataAddress = None
            data = None

        if self.mSoleVertexBuffer is None:
            desc = OpenMayaRender.MVertexBufferDescriptor('', OpenMayaRender.MGeometry.kPosition, OpenMayaRender.MGeometry.kFloat, 3)
            self.mSoleVertexBuffer = OpenMayaRender.MVertexBuffer(desc)

            dataAddress = self.mSoleVertexBuffer.acquire(soleCount, True)
            data = ((ctypes.c_float*3)*soleCount).from_address(dataAddress)

            for i in range(soleCount):
                data[i][0] = sole[i][0]
                data[i][1] = sole[i][1]
                data[i][2] = sole[i][2]

            self.mSoleVertexBuffer.commit(dataAddress)
            dataAddress = None
            data = None

        if self.mHeelVertexBuffer is None:
            desc = OpenMayaRender.MVertexBufferDescriptor('', OpenMayaRender.MGeometry.kPosition, OpenMayaRender.MGeometry.kFloat, 3)
            self.mHeelVertexBuffer = OpenMayaRender.MVertexBuffer(desc)

            dataAddress = self.mHeelVertexBuffer.acquire(heelCount, True)
            data = ((ctypes.c_float*3)*heelCount).from_address(dataAddress)

            for i in range(heelCount):
                data[i][0] = sole[i][0]
                data[i][1] = sole[i][1]
                data[i][2] = sole[i][2]

            self.mHeelVertexBuffer.commit(dataAddress)
            dataAddress = None
            data = None

        if self.mSoleWireIndexBuffer is None:
            count = 2 * (soleCount-1)
            rawData = [0, 1,
                       1, 2,
                       2, 3,
                       3, 4,
                       4, 5,
                       5, 6,
                       6, 7,
                       7, 8,
                       8, 9,
                       9, 10,
                       10, 11,
                       11, 12,
                       12, 13,
                       13, 14,
                       14, 15,
                       15, 16,
                       16, 17,
                       17, 18,
                       18, 19,
                       19, 20]

            self.mSoleWireIndexBuffer = OpenMayaRender.MIndexBuffer(OpenMayaRender.MGeometry.kUnsignedInt32)

            dataAddress = self.mSoleWireIndexBuffer.acquire(count, True)
            data = (ctypes.c_uint*count).from_address(dataAddress)

            for i in range(count):
                data[i] =  rawData[i]

            self.mSoleWireIndexBuffer.commit(dataAddress)
            dataAddress = None
            data = None

        if self.mHeelWireIndexBuffer is None:
            count = 2*(heelCount-1)
            rawData = [0, 1,
                       1, 2,
                       2, 3,
                       3, 4,
                       4, 5,
                       5, 6,
                       6, 7,
                       7, 8,
                       8, 9,
                       9, 10,
                       10, 11,
                       11, 12,
                       12, 13,
                       13, 14,
                       14, 15,
                       15, 16]
            self.mHeelWireIndexBuffer = OpenMayaRender.MIndexBuffer(OpenMayaRender.MGeometry.kUnsignedInt32)

            dataAddress = self.mHeelWireIndexBuffer.acquire(count, True)
            data = (ctypes.c_uint * count).from_address(dataAddress)

            for i in range(count):
                data[i] = rawData[i]

            self.mHeelWireIndexBuffer.commit(dataAddress)
            dataAddress = None
            data = None

        if self.mSoleShadedIndexBuffer is None:
            count = 3 * (soleCount - 2)
            rawData = [0, 1, 2,
                       0, 2, 3,
                       0, 3, 4,
                       0, 4, 5,
                       0, 5, 6,
                       0, 6, 7,
                       0, 7, 8,
                       0, 8, 9,
                       0, 9, 10,
                       0, 10, 11,
                       0, 11, 12,
                       0, 12, 13,
                       0, 13, 14,
                       0, 14, 15,
                       0, 15, 16,
                       0, 16, 17,
                       0, 17, 18,
                       0, 18, 19,
                       0, 19, 20]

            self.mSoleShadedIndexBuffer = OpenMayaRender.MIndexBuffer(OpenMayaRender.MGeometry.kUnsignedInt32)

            dataAddress = self.mSoleShadedIndexBuffer.acquire(count, True)
            data = (ctypes.c_uint*count).from_address(dataAddress)

            for i in range(count):
                data[i] = rawData[i]

            self.mSoleShadedIndexBuffer.commit(dataAddress)
            dataAddress = None
            data = None

        if self.mHeelShadedIndexBuffer is None:
            count = 3*(heelCount-2)
            rawData = [0, 1, 2,
                       0, 2, 3,
                       0, 3, 4,
                       0, 4, 5,
                       0, 5, 6,
                       0, 6, 7,
                       0, 7, 8,
                       0, 8, 9,
                       0, 9, 10,
                       0, 10, 11,
                       0, 11, 12,
                       0, 12, 13,
                       0, 13, 14,
                       0, 14, 15,
                       0, 15, 16]

            self.mHeelShadedIndexBuffer = OpenMayaRender.MIndexBuffer(OpenMayaRender.MGeometry.kUnsignedInt32)

            dataAddress = self.mHeelShadedIndexBuffer.acquire(count, True)
            data = (ctypes.c_uint * count).from_address(dataAddress)

            for i in range(count):
                data[i] = rawData[i]

            self.mHeelShadedIndexBuffer.commit(dataAddress)
            dataAddress = None
            data = None

        return True

# gl Draw Declaration
class footPrintDrawAgentGL(footPrintDrawAgent):
    def __init__(self):
        super(footPrintDrawAgentGL, self).__init__()

    def getShaderCode(self):
        shaderCode = """
                float4x4 gWVXf : WorldView;
                float4x4 gPXf : Projection;
                float4 matColor = float4(0.8, 0.2, 0.0, 1.0);
                float scale = 1.0;
                
                struct appdata 
                {
                 float3 position : POSITION;
                };
                
                struct vsOutput {
                   float4 position : POSITION;
                   };
                   
                vsOutput footPrintVS(appdata IN)
                {
                   float4x4 scaleMat = float4x4(scale, 0, 0, 0,
                                                  0, scale, 0, 0,
                                                  0, 0, scale, 0,
                                                  0, 0, 0, 1);
                   float4x4 transform = mul(gPXf, mul(gWVXf, scaleMat));
                   
                   vsOutput OUT;
                   OUT.position = mul(transform, float4(IN.position, 1));
                   return OUT;
                   }
                   
                   float4 footPrintPS(vsOutput IN) : COLOR
                   {
                   return matColor;
                   }
                   
                   technique Main
                   {
                   pass p0
                   {
                   VertexShader = compile glslv footPrintVS();
                   PixelShader = compile glslf footPrintPS();
               }
           }
        """
        return shaderCode

# DX draw Agent Declaration
class footPrintDrawAgentDX(footPrintDrawAgent):
    def __init__(self):
        footPrintDrawAgent.__init__(self)

    def getShaderCode(self):
        shaderCode = """
        extern float4x4 gWVXf : WorldView;
        extern float4x4 gPXf : Projection;
        extern float4 matColor = float4(0.8, 0.2, 0.0, 1.0);
        extern float scale = 1.0;
        
        struct appdata {
            float3 position : POSITION;
        };
        
        struct vsOutput {
            float4 position : SV_Position;
        };
        
        vsOutput footPrintVS(appdata IN)
        {
        float4x4 scaleMat = float4x4(scale, 0, 0, 0,
                                    0, scale, 0, 0,
                                    0, 0, scale, 0,
                                    0, 0, 0, 1);
        float4x4 transform = mul(mul(scaleMat, gWVXf), gPXf);
    
        vsOutput OUT;
        OUT.position = mul(float4(IN.position, 1), transform);
        return OUT;
    }
  
    float4 footPrintPS(vsOutput IN) : SV_Target
    {
        return matColor;
    }
    
    technique10 Main
    {
        pass p0
        {
            SetVertexShader( CompileShader( vs_5_0, footPrintVS() ));
            SetGeometryShader( NULL );
            SetPixelShader( CompileShader( ps_5_0, footPrintPS() ));
        }
    }
"""
        return shaderCode
blendState = None
rasterState = None
drawAgent = None

class footPrintDrawOverride(OpenMayaRender.MPxDrawOverride):
    @staticmethod
    def creator(obj):
        return footPrintDrawOverride(obj)

    @staticmethod
    def draw(context, data):
        # get user draw data, data is footPrintData class
        # context is MFrameContext Class, contains some global information for the current render frame.
        # This includes information such as render targets, viewport size and camera information.
        footData = data

        # footData must be instance of footPrintData declared above
        if not isinstance(footData, footPrintData):
            return

        # get dag object draw override info
        objectOverrideInfo = footData.fDrawOV

        # sample code to determinate the rendering destination
        debugDestination = False
        if debugDestination:
            destination = context.renderingDestination()
            destinationType = '3d viewport'
            if destination[0] == OpenMayaRender.MFrameContext.k2dViewport:
                destinationType = '2d viewport'

            elif destination[0] == OpenMayaRender.MFrameContext.kImage:
                destinationType = 'image'

            print 'footprint node render destination is' + destinationType + '. Destination name=' + str(destination[1])

        # just return and draw nothing, if it is override invisible
        if objectOverrideInfo.overrideEnabled and not objectOverrideInfo.enableVisible:
            return

        # Get display status
        displayStyle = context.getDisplayStyle()
        drawAsBoundingbox = (displayStyle & OpenMayaRender.MFrameContext.kBoundingBox) or (objectOverrideInfo.lod == OpenMaya.MDAGDrawOverrideInfo.kLODBoundingBox)
        ## If we don't want to draw the bounds within this plugin
        ## manually, then skip drawing altogether in bounding box mode
        ## since the bounds draw is handled by the renderer and
        ## doesn't need to be drawn here.
        ##

        if drawAsBoundingbox and not footData.fCustomBoxDraw:
            return

        animPlay = OpenMayaAnim.MAnimControl.isPlaying()
        animScrub = OpenMayaAnim.MAnimControl.isScrubbing()
        # if in playback but hidden in playback, skip drawing
        if (animPlay or animScrub) and not objectOverrideInfo.playbackVisible:
            return

        # for ani viewport interaction switch to bounding box mode,
        # except when we are in playback
        if context.inUserInteraction() or context.userChangingViewContext():
            if not animPlay and not animScrub:
                drawAsBoundingbox = True

        # now, something gonna draw...

        ## Check to see if we are drawing in a shadow pass.
        ## If so then we keep the shading simple which in this
        ## example means to disable any extra blending state changes

        passCtx = context.getPassContext()
        passSemantics = passCtx.passSemantics()
        castingShadows = False
        for semantic in passSemantics:
            if semantic == OpenMayaRender.MPassContext.kShadowPassSemantic:
                castingShadows = True

        debugPassInformation = False
        if debugPassInformation:
            passId = passCtx.passIdentifier()
            print 'footprint node drawing in pass[' + str(passId) + '], semantic[' + str(passSemantics) + ']'

        # get cached data
        multiplier = footData.fMultiplier
        color = [footData.fColor[0], footData.fColor[1], footData.fColor[2], 1.0]

        requireBlending = False

        # If we are not casting shadows then do extra work
        # for display styles
        if not castingShadows:
            # use some monotone version of color to show 'default material mode'
            if displayStyle & OpenMayaRender.MFrameContext.kDefaultMaterial:
                color[0] = color[1] = color[2] = (color[0] + color[1] + color[2])/3.0

            # do some alpha blending in xrayMode
            elif displayStyle & OpenMayaRender.MFrameContext.kXray:
                requireBlending = True
                color[3] = 0.3

        # set blend and raster state
        stateMgr = context.getStateManager()
        oldBlendState = None
        oldRasterState = None
        rasterStateModified = False

        if stateMgr is not None and (displayStyle & OpenMayaRender.MFrameContext.kGouraudShaded):
            # draw filled, and with blending if required
            if requireBlending:
                global blendState
                if blendState is None:
                    desc = OpenMayaRender.MBlendStateDesc()
                    desc.targetBlends[0].blendEnable = True
                    desc.targetBlends[0].destinationBlend = OpenMayaRender.MBlendStatekInvSourceAlpha
                    desc.targetBlends[0].alphaDestinationBlend = OpenMayaRender.MBlendStatekInvSourceAlpha
                    blendState = stateMgr.acquireBlendState(desc)

                if blendState is not None:
                    oldBlendState = stateMgr.acquireBlendState(desc)
                    stateMgr.setBlendState(blendState)

            # Override culling mode since we always want double-sided
            oldRasterState = stateMgr.getRasterizerState()
            if oldRasterState:
                desc = oldRasterState.desc()
                # It's also possible to change this to kCullFront of kCullBack if we
                # wanted to set it to that
                cullMode = OpenMayaRender.MRasterizerState.kCullNone
                if desc.cullMode != cullMode:
                    global rasterState
                    if rasterState is not None:
                        desc.cullMode = cullMode
                        rasterState = stateMgr.acquireRasterizerState(desc)

                    if rasterState is not None:
                        rasterStateModified = True
                        stateMgr.setRasterizerState(rasterState)

        ######################
        # Start the draw work
        ######################
        # prepare draw Agent, default using OpenGL
        global drawAgent
        if drawAgent is None:
            if OpenMayaRender.MRenderer.drawAPIIsOpenGL():
                drawAgent = footPrintDrawAgentGL()
            else:
                drawAgent = footPrintDrawAgentDX()

        if not drawAgent is None:

            drawAgent.beginDraw(context, color, multiplier)

            if drawAsBoundingbox:
                drawAgent.drawBoundingBox(context)

            else:
                # templated, only draw wireFrame and it is not selectable
                overrideTemplated = objectOverrideInfo.overrideEnabled and objectOverrideInfo.displayType == OpenMaya.MDAGDrawOverrideInfo.kDisplayTypeTemplate
                # Override no shaded, only show wireframe
                overrideNoShaded = objectOverrideInfo.overrideEnabled and objectOverrideInfo.enableShading

                if overrideTemplated or overrideNoShaded:
                    drawAgent.drawWireframe(context)

                else:
                    if (displayStyle & OpenMayaRender.MFrameContext.kGouraudShaded) or (displayStyle & OpenMayaRender.MFrameContext.kTextured):
                        drawAgent.drawShaded(context)

                    if (displayStyle & OpenMayaRender.MFrameContext.kWireFrame):
                        drawAgent.drawWireframe(context)

            drawAgent.endDraw(context)

        #############################
        # End the draw work
        #############################
        # restore old blend state and old raster state

        if stateMgr is not None and (displayStyle & OpenMayaRender.MFrameContext.kGouraudShaded):
            if oldBlendState is not None:
                stateMgr.setBlendState(oldBlendState)

            if rasterStateModified and oldRasterState is not None:
                stateMgr.setRasterizerState(oldRasterState)

    def __init__(self, obj):
        OpenMayaRender.MPxDrawOverride.__init__(self, obj, footPrintDrawOverride.draw)

        ## We want to perform custom bounding box drawing
        ## so return True so that the internal rendering code
        ## will not draw it for us.
        self.mCustomBoxDraw = False  # REVIEW original value was True
        self.mCurrentBoundingBox = OpenMaya.MBoundingBox()

    def supportedDrawAPIs(self):
        # this plugin supports both GL and DX
        return OpenMayaRender.MRenderer.kOpenGL | OpenMayaRender.MRenderer.kDirectX11

    def isBounded(self, objPath, cameraPath):
        return True

    def boundingBox(self, objPath, cameraPath):
        corner1 = OpenMaya.MPoint(-0.17, 0.0, -0.7)
        corner2 = OpenMaya.MPoint(0.17, 0.0, 0.3)

        multiplier = self.getMultiplier(objPath)
        corner1 *= multiplier
        corner2 *= multiplier

        self.mCurrentBoundingBox.clear()
        self.mCurrentBoundingBox.expand(corner1)
        self.mCurrentBoundingBox.expand(corner2)

        return self.mCurrentBoundingBox

    def disableInternalBoundingBoxDraw(self):
        return self.mCustomBoxDraw

    def prepareForDraw(self, objPath, cameraPath, frameContext, oldData):
        # retrieve data cache (create if does not exist)
        data = oldData
        if not isinstance(data, footPrintData):
            data = footPrintData()

        # compute data and cache it
        data.fMultiplier = self.getMultiplier(objPath)
        color = OpenMayaRender.MGeometryUtilities.wireframeColor(objPath)
        data.fColor = [color.r, color.g, color.b]
        data.fCustomBoxDraw = self.mCustomBoxDraw

        # Get the draw override  information
        data.fDrawOV = objPath.getDrawOverrideInfo()

        return data

    def hasUIDrawables(self):
        return True

    def addUIDrawables(self, objPath, drawManager, frameContext, data):
        # draw a text foot
        pos = OpenMaya.MPoint(0.0, 0.0, 0.0) # position of the text
        textColor = OpenMaya.MColor((0.1, 0.8, 0.8, 1.0)) # text color

        drawManager.beginDrawable()

        drawManager.setColor(textColor)
        drawManager.setFontSize(OpenMayaRender.MUIDrawManager.kSmallFontSize)
        drawManager.text(pos, 'FootPrint', OpenMayaRender.MUIDrawManager.kCenter)

        # search info about beginDrawable() and endDrawable()
        drawManager.endDrawable()

    def getMultiplier(self, objPath):
        # retrieve  value of the size attribute from the node
        footPrintNode = objPath.node()
        plug = OpenMaya.MPlug(footPrintNode, footPrint.size)
        if not plug.isNull:
            sizeVal = plug.asMDistance()
            return sizeVal.asCentimeters()

        return  1.0

def initializePlugin(obj):
    plugin = OpenMaya.MFnPlugin(obj, 'Autodesk', '3.0', 'Any')
    try:
        plugin.registerNode('footPrint', footPrint.id, footPrint.creator, footPrint.initialize, OpenMaya.MPxNode.kLocatorNode, footPrint.drawDbClassification)
    except:
        sys.stderr.write('Failed to register node /n')
        raise

    try:
        OpenMayaRender.MDrawRegistry.registerDrawOverrideCreator(footPrint.drawDbClassification, footPrint.drawRegistrantId, footPrintDrawOverride.creator)
    except:
        sys.stderr.write('Failed to register override /n')
        raise

def uninitializePlugin(obj):
    plugin = OpenMaya.MFnPlugin(obj)
    try:
        plugin.deregisterNode(footPrint.id)
    except:
        sys.stderr.write('Failed to deregister node /n')
        pass

    try:
        OpenMayaRender.MDrawRegistry.deregisterDrawOverrideCreator(footPrint.drawDbClassification, footPrint.drawRegistrantId)
    except:
        sys.stderr.write('Failed to deregister override /n')
        pass

"""
to load

from Nodes import footPrint 
# reload(footPrint)
from maya import cmds
try:
    # Force is important 
    cmds.unloadPlugin('footPrint', force=True)
finally:
    cmds.loadPlugin(footPrint.__file__)
    
cmds.createNode('footPrint')
"""