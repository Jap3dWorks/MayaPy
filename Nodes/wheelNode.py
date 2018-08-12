import sys
from maya import OpenMaya
from maya import OpenMayaMPx

nodeName = 'WheelNode'
# identifier of the node
nodeId = OpenMaya.MTypeId(0x100fff)

# we use the maya proxy as base class for our node
class WheelNode(OpenMayaMPx.MPxNode):
    # now define inputs as MObject(), which are a handler
    inRadius = OpenMaya.MObject()
    inTranslate = OpenMaya.MObject()

    # Define output Value
    outRotate = OpenMaya.MObject()

    def __init__(self):
        super(WheelNode, self).__init__()

    # compute is the name that the method have to be, where the logic is
    def compute(self, plug, dataBlock):
        """
        formula: translate / (2 * 3.14 * radius) * (-360)

        """
        if plug == self.outRotate:
            dataHandleRadius = dataBlock.inputValue(self.inRadius)
            dataHandleTranslate = dataBlock.inputValue(self.inTranslate)

            # transform inputs to a type of data we can manipulate, in this case float
            inRadiusVal = dataHandleRadius.asFloat()
            inTranslateVal = dataHandleTranslate.asFloat()

            # for prevent a 0 int, we put float("formula")
            outRotate = float(inTranslateVal) / float(2 * 3.14 * inRadiusVal) * (-360)

            dataHandleRotate = dataBlock.outputValue(self.outRotate)

            dataHandleRotate.setFloat(outRotate)
            dataBlock.setClean(plug)

        else:
            return OpenMaya.kUnknownParameter

# functions maya needs to create and register nodes
def nodeCreator(self):
    return OpenMayaMPx.asMPxPtr(WheelNode())

def nodeInitializer(self):
    # 1. creating function set for numeric attributes
    mFnAttr = OpenMaya.MFnNumericAttribute()

    # 2. create attributes
    WheelNode.inRadius = mFnAttr.create('radius', 'r', OpenMaya.MFnNumericData.kFloat, 0.0)
    mFnAttr.setReadable(1)
    mFnAttr.setWritable(1)
    mFnAttr.setStorable(1)
    mFnAttr.setKeyable(1)

    WheelNode.inTranslate = mFnAttr.create('translate', 't', OpenMaya.MFnNumericData.kFloat, 0.0)
    mFnAttr.setReadable(1)
    mFnAttr.setWritable(1)
    mFnAttr.setStorable(1)
    mFnAttr.setKeyable(1)

    WheelNode.outRotate = mFnAttr.create('rotate', 'ro', OpenMaya.MFnNumericData.kFloat, 0.0)
    mFnAttr.setReadable(1)
    mFnAttr.setWritable(0)
    mFnAttr.setStorable(0)
    mFnAttr.setKeyable(0)

    # 3. Attaching the attributes to the Node
    WheelNode.addAttribute(WheelNode.inRadius)
    WheelNode.addAttribute(WheelNode.inTranslate)
    WheelNode.addAttribute(WheelNode.outRotate)

    # 4. Design Circuitry
    WheelNode.attributeAffects(WheelNode.inRadius, WheelNode.outRotate)
    WheelNode.attributeAffects(WheelNode.inTranslate, WheelNode.outRotate)

def initializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.registerNode(nodeName, nodeId, nodeCreator, nodeInitializer)

    except:
        sys.stderr.write('Failed to register command: %s' %nodeName)

 # uninitialize script plugin
def uninitializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.deregisterNode(nodeName)
    except:
        sys.stderr.write('Failed to unregister command: %s' %nodeName)