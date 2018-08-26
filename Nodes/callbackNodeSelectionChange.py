import maya.api.OpenMaya as OpenMaya
import sys

def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, objects created using the Maya Python API 2.0.
    """
    pass


class CBSelChange(OpenMaya.MPxNode):
    nodeName = 'CBSelChangeNode'
    nodeID = OpenMaya.MTypeId(0x100fff)

    idCallback = []

    @classmethod
    def creator(cls):
        return cls()

    @staticmethod
    def initializer():
        pass

    def __init__(self):
        super(CBSelChange, self).__init__()
        # Event callback
        self.idCallback.append(OpenMaya.MEventMessage.addEventCallback('SelectionChanged', self.callbackFunc))
        # DG callback
        self.idCallback.append(OpenMaya.MDGMessage.addNodeRemovedCallback(self.remove, 'dependNode'))

    def callbackFunc(self, *args):
        # get active selection
        mSel = OpenMaya.MSelectionList()
        mSel.merge(OpenMaya.MGlobal.getActiveSelectionList())
        print ('{0} print a callback, item selected: {1}'.format(self.nodeName, mSel))

    def remove(self, *args):
        # Try to get this node, if it return error, the node do not exist
        try:
            OpenMaya.MSelectionList.add(self.thisMObject())

        except:
            # Remove callbacks
            for i in xrange(len(self.idCallback)):
                # selection callback
                try:
                    OpenMaya.MEventMessage.removeCallback(self.idCallback[i])
                except:
                    pass
                # node callback
                try:
                    OpenMaya.MDGMessage.removeCallback(self.idCallback[i])
                except:
                    pass

    def compute(self):
        pass

def initializePlugin(mobject):
    plugin = OpenMaya.MFnPlugin(mobject)
    try:
        plugin.registerNode(CBSelChange.nodeName, CBSelChange.nodeID, CBSelChange.creator, CBSelChange.initializer, OpenMaya.MPxNode.kDependNode)
    except:
        sys.stderr.write('Failed register plugin: %s' % CBSelChange.nodeName)
        raise

def uninitializePlugin(mobject):
    plugin = OpenMaya.MFnPlugin(mobject)
    try:
        plugin.deregisterNode(CBSelChange.nodeID)

    except:
        sys.stderr.write('Failed unregister plugin: %s' % CBSelChange.nodeName)
        pass

