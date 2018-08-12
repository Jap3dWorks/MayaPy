import sys
from maya import OpenMaya
from maya import OpenMayaMPx
from maya import OpenMayaRender

nodeName = 'LeftFoot'
nodeId = OpenMaya.MTypeId(0x100fff)

# check if this is works on viewport2.0
glRenderer = OpenMayaRender.MHardwareRenderer.theRenderer()
glFT = glRenderer.glFunctionTable()

class LocatorNode(OpenMayaMPx.MPxLocatorNode):

    def __init__(self):
        super(LocatorNode, self).__init__()

    def compute(self, plug, dataBlock):
        return OpenMaya.kUnknownParameter

    def draw(self, view, path, style, status):
        # beginGl and endGL tells maya that we are going to use OpenGL commands between them.
        view.beginGL()
        # pushed current state. glPushAttrib take a mask
        # that indicates which group of states variables save on the attribute stack.
        # GL_CURRENT_BIT current RGBA color
        # MGL_ refer OpenGL (GL_) functions in maya. maya has it's oun implementation.
        glFT.glPushAttrib(OpenMayaRender.MGL_CURRENT_BIT)
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

        # Draw a shape.
        # glBegin allow us to enter in primitive draw mode.
        # glEnd shut down communication with graphic card and return to the main program.
        glFT.glBegin(OpenMayaRender.MGL_POLYGON)
        # define points.
        glFT.glVertex3f(-0.031, 0, -2.875)
        glFT.glVertex3f(-0.939, 0.1, -2.370)
        glFT.glVertex3f(-1.175, 0.2, -1.731)
        glFT.glVertex3f(-0.603, 0.3, 1.060)
        glFT.glVertex3f(0.473, 0.3, 1.026)
        glFT.glVertex3f(0.977, 0.2, -1.731)
        glFT.glVertex3f(0.809, 0.1, -2.337)
        glFT.glVertex3f(0.035, 0, -2.807)
        # end communication with graphic card
        glFT.glEnd()

        # Draw another shape
        glFT.glBegin(OpenMayaRender.MGL_POLYGON)
        glFT.glVertex3f(-0.587, 0.3, 1.33)
        glFT.glVertex3f(0.442, 0.3, 1.33)
        glFT.glVertex3f(0.442, 0.3, 1.92)
        glFT.glVertex3f(0.230, 0.3, 2.24)
        glFT.glVertex3f(-0.442, 0.3, 2.25)
        glFT.glVertex3f(-0.635, 0.3, 1.92)
        glFT.glVertex3f(-0.567, 0.3, 1.35)
        glFT.glEnd()

        # Define colors for different selection modes
        # TODO -> diferent test with this values, try to comment this lines too
        if status == view.kActive:
            glFT.glColor4f(0.2, 0.5, 0.1, 1)
        elif status == view.kLead:
            glFT.glColor4f(0.5, 0.2, 0.1, 1)
        elif status == view.kDormant:
            glFT.glColor4f(0.1, 0.1, 0.1, 1)

        view.drawText('Left Foot', OpenMaya.MPoint(0,0,0), view.kLeft)
        # Disable blend mode
        glFT.glDisable(OpenMayaRender.MGL_BLEND)
        # restore the state
        glFT.glPopAttrib()
        view.endGL()

def nodeCreator():
    return OpenMayaMPx.asMPxPtr(LocatorNode())

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
    cmds.unloadPlugin('LeftFoot', force=True)
finally:
    cmds.loadPlugin(LocatorNode.__file__)
    
cmds.createNode('LeftFoot')
"""