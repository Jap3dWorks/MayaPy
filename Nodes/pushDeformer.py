# open maya 2.0 doesn't support create nodes

from maya import OpenMaya as om
import maya.OpenMayaMPx as ompx
import maya.cmds as cmds

# the api changed somewhat so we need to get the right attributes

kApiVersion = cmds.about(apiVersion=True)
if kApiVersion < 201600:
    inputAttr = ompx.cvar.MPxDeformerNode_input
    inputGeomAttr = ompx.cvar.MPxDeformerNode_inputGeom
    outputGeomAttr = ompx.cvar.MPxDeformerNode_outputGeom
    envelopeAttr = ompx.cvar.MPxDeformerNode_envelope

else:

class PushDeformer(ompx.MPxDeformerNode):
    # setup the ID
    id = om.MTypeId(0x01012)
    # setup the name
    name = 'push'

    # now add the attributes we will be using
    # unlike openmaya 2, we need to use an empty MObject here instead of none
    push = om.MObject()

    @classmethod
    def creator(cls):
        # unlike openMaya 2, we need to return this as MPxPtr instead
        return ompx.asMPxPtr(cls())

    @staticmethod
    def initialize():
        nAttr = om.MFnNumericAttribute()

        PushDeformer.push = nAttr.create('push', 'p', om.MFnNumericData.kFloat, 0.0)
        nAttr.setKeyable(True)
        nAttr.setStorable(True)
        nAttr.setChannelBox(True)

        PushDeformer.addAttribute(PushDeformer.push)
        PushDeformer.attributeAffects(PushDeformer.push, outputGeomAttr)

        # make our node paintable
        cmds.makePaintable(
            PushDeformer.name,
            'weights',
            attrType='multiFloat',
            shapeMode='deformer'
        )

    def deform(self, data, geoIterator, matrix, geometryIndex):
        # get push value
        # data is a class?
        pushHandle = data.inputValue(self.push)
        push = pushHandle.asFloat()

        # get envelope value
        envelopeHandle = data.inputValue(envelopeAttr)
        envelope = envelopeHandle.asFloat()

        # get the input geometry
        mesh = self.getInputMesh(data, geometryIndex)

        # crete an empty array (list) of floats vectors to store our normals
        normals = om.MFloatVectorArray()
        # the make de meshFn to interact with the mesh
        meshFn = om.MFnMesh(mesh)
        # use this to get and store the normals froms the mesh onto the normals array 'normals'
        # remember pay attention to the pluralization of the normals
        meshFn.getVertexNormals(
            # if True, the normals are angleWeighted which is what we want
            True,
            # we tell were store normals, in this case normals above
            normals,
            # finally tell the space, in this case object space
            om.MSpace.kTransform
        )

        # now we can iterate throught the geometry vertices and do our deformation
        while not geoIterator.isDone(): # geo iterator is ...
            # current point index
            index = geoIterator.index()
            # look normal from our array
            normal = om.MVector(normals[index]) # index may be int
            # get the positions of the point
            position = geoIterator.position()
            # calculate the offset
            # multiply vector by magnitude
            offset = (normal * push * envelope) # push is the input value //

            # we then query the painted weitght for this area
            weight = self.weightValue(data, geometryIndex, index) # from MPxDeformerNode class
            offset = (offset * weight)

            # Finally we can set the position
            geoIterator.setPosition(position + offset)
            # go to the next item
            geoIterator.next()



    def getInputMesh(self, data, geomIdx):
        # we need to check the input of the node
        inputHandle = data.outputArrayValue(inputAttr)
        inputHandle.jumpToElement(geomIdx)
        # Once we have the input handle, we get its values, then find the children mesh and get it as a mesh MObject
        mesh = inputHandle.outputValue().child(inputGeomAttr).asMesh()
        return mesh

def initializePlugin(plugin):
    pluginFn = ompx.MFnPlugin(plugin)
    try:
        pluginFn.registerNode(
            PushDeformer.name,
            PushDeformer.id,
            PushDeformer.creator,
            PushDeformer.initialize,
            ompx.MPxNode.kDeformerNode # one xtra argument to tell the type of node
        )
    except:
        om.MGlobal.displayError('Failed to register node: %s' % PushDeformer.name)
        raise

def uninitializePlugin(plugin):
    pluginFn = ompx.MFnPlugin(plugin)
    try:
        pluginFn.deregisterNode(PushDeformer.id)

    except:
        om.MGlobal.displayError('Failed to unregister node: %s' % PushDeformer.name)
        raise

"""
    to load:
    from Nodes import pushDeformer
    import maya.cmds as mc
    try:
        # Force is important 
        mc.unloadPlugin('pushDeformer', force=True)
    finally:
        mc.loadPlugin(pushDeformer.__file__)
        
    mc.polySphere()
    mc.deformer(type='push')
"""