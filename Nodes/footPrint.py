# TODO Maya api 2 and compatibility with maya viewport 2
# https://help.autodesk.com/view/MAYAUL/2018/ENU/?guid=__py_ref_scripted_2py_draw_foot_printby_render_utilities_8py_example_html

import ctypes
import sys
import maya.api.OpenMayaUI as OpenMayaUI
import maya.api.OpenMaya as OpenMaya
import maya.api.OpenMayaMPx as OpenMayaMPx
import maya.api.OpenMayaRender as OpenMayaRender
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
# TODO experiments saving point in json files and then change the locator shape
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

#############################################
# node implementation with standart viewport
#############################################
class footPrint(OpenMayaMPx.MPxLocatorNode):
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
        # Functionset for creating and working with angle, distance and time attributes
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
        thisNode = self.thisMObject()
        plug = om.MPlug(thisNode, footPrint.size)
        sizeVal = plug.asMDistance()
        multiplier = sizeVal.asCentimeters()

        global sole, soleCount
        global heel, heelCount

        # beginGl and endGL tells maya that we are going to use OpenGL commands between them.
        view.beginGL()

        # drawing in VP1 will be done using V1 pythons API
        glRenderer = OpenMayaRender1.MHardwareRenderer.theRenderer()
        glFT = glRenderer.glFunctionTable()

        if (style==OpenMayaUI.M3dView.kFlatShaded) or (style==OpenMayaUI.M3dView.kGouraudShaded):
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
        # read about thisMObject func
        thisNode = self.thisMObject()
        plug = OpenMaya.MPlug(thisNode, footPrint.size)
        sizeVal = plug.asMDistance()
        multiplier = sizeVal.asCentimeters()

        corner1 = OpenMaya.MPoint(-0.17, 0.0, -0.7)
        corner2 = OpenMaya.MPoint(0.17, 0.0, 0.3)

        corner1 *= multiplier
        corner2 *= multiplier

        return OpenMaya.MBoundingBox(corner1, corner2)

##################################
# Maya viewport2 implementation
##################################

def nodeCreator():
    return OpenMayaMPx.asMPxPtr(footPrint())

def nodeInitializer():
    pass

def initializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.registerNode(nodeName, nodeId, nodeCreator, nodeInitializer, OpenMayaMPx.MPxNode.kLocatorNode)
    except:
        sys.stderr.write('Failed to register node: %s' %nodeName)

def uninitializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.deregisterNode(nodeName)
    except:
        sys.stderr.write('Failed to unregister node: %s' %nodeName)

"""
to load

from Nodes import LocatorNode
# reload(LocatorNode)
from maya import cmds
try:
    # Force is important 
    cmds.unloadPlugin('footPrint', force=True)
finally:
    cmds.loadPlugin(LocatorNode.__file__)
    
cmds.createNode('LeftFoot')
"""