# documentation: http://evgeniyzaitsev.com/2010/07/28/60/
import pymel.core as pm
import maya.api.OpenMaya as OpenMaya
import os

import logging
logging.basicConfig()
logger = logging.getLogger('Fbx Exporter:')
logger.setLevel(logging.INFO)

class FbxExporter(list):
    attrBoolName = 'exp'
    attrPathName = 'FbxExpPath'
    attrCompoundName = 'FbxExporter'
    defaultPath = os.getenv('MAYA_APP_DIR')

    # Instance variable holds on to the instance of this manager
    _instance = None
    # we have an instance class that prevents us creating multiple of this same class
    # todo: better warning messages for instanced class, and error if class is called without .instance()
    @classmethod
    def instance(cls):
        # if _instance = None, create a class instance
        if cls._instance == None:
            cls._instance = cls()
        else:
            logger.warn('Is already an instance: %s' % cls)
        # returns a instance of the class stored in _instance
        return cls._instance

    __doc__ = """
                    Fbx Exporter V1.0.
                    FbxExporter.instance() for singleton
                    Export object and children to a fbx.
                    This script add two attributes to a transform node only.
                        exp(boolean): indicate if is exportable
                        path(string): path where objects will be export

                    Then construct a list of pymel.core.nodetypes.Transform objects

                    Methods:
                        fbxExporter.addAtribute(): add attributes
                        fbxExporter.RemoveAttr(): remove attributes
                        fbxExporter.export():export items with the {0} attribute True""".format(attrBoolName)

    def __init__(self):
        """
        On creation, search exportable objects in scene with the attributes
        """
        super(FbxExporter, self).__init__()

        # Construct list
        self.constructList()

    def constructList(self):
        """
        This method refresh and fill the self.list
        """
        # clear previous list and all references
        del self[:]

        # search items and extend list
        self.extend(self.__findAttr(self.attrCompoundName))
        logger.debug('constructList: Class list items:%s items found: %s' % (len(self), self))

    def __findAttr(self, attr, *args):
        """
        Args:
            attr: Attribute desired
            args: objects we want to check, if no args check entire scene

        Returns: Pymel.core.nodetypes.Transform objects List with the attribute
        """
        mselList = OpenMaya.MSelectionList()
        # if some args are given
        if len(args):
            for i in args:
                mselList.add(i)
        # no args check entire scene
        else:
            mselList.add('*')  # add all scene

        # msellist iterator
        mselList_It = OpenMaya.MItSelectionList(mselList, OpenMaya.MFn.kTransform)

        transformReturn = []

        while not mselList_It.isDone():
            transform = mselList_It.getDagPath()
            transform_mfn = OpenMaya.MFnTransform(transform)

            # Check if obj has the attribute
            if transform_mfn.hasAttribute(attr):
                transformReturn.append(pm.PyNode(transform))

            mselList_It.next()

        return transformReturn

    def addAttributes(self, path=defaultPath):
        """
        This method adds the attributes necessary to use the script.
        At the end, refresh the self list.
        Is necessary use constructList after this method for refresh the items list
        Args:
            path: path where export the fbx
        """
        # todo: extract attr creation out of the loop
        # get active selection
        mSelList = OpenMaya.MGlobal.getActiveSelectionList()
        mSelList_It = OpenMaya.MItSelectionList(mSelList, OpenMaya.MFn.kTransform)

        # iterate and find if items with the attribute, if have not, add.
        while not mSelList_It.isDone():
            transform = mSelList_It.getDagPath()
            transform_DN = mSelList_It.getDependNode()
            transform_fn = OpenMaya.MFnTransform(transform)

            # create attributes
            fAttr = OpenMaya.MFnNumericAttribute()
            boolAttr = fAttr.create(self.attrBoolName, self.attrBoolName, OpenMaya.MFnNumericData.kBoolean, True)  # get an mObject atttr
            fAttr.keyable = True
            fAttr.storable = True
            fAttr.readable = True
            fAttr.writable = True

            # compoundAttr
            fAttr = OpenMaya.MFnCompoundAttribute()
            compoundAttr = fAttr.create(self.attrCompoundName, 'fe')
            fAttr.addChild(boolAttr)
            fAttr.keyable = True
            fAttr.storable = True
            fAttr.readable = True
            fAttr.writable = True

            # check if we have yet the attribute
            if transform_fn.hasAttribute(self.attrBoolName):
                logger.info('%s already has attribute: %s' % (transform, self.attrBoolName))
            else:
                # add attribute if it does not exist in the node
                transform_fn.addAttribute(compoundAttr)
                self.addExtraPathAttr(transform_DN,path)


            mSelList_It.next()


    def addExtraPathAttr(self, transform, path=defaultPath):
        """
        add extra path attribute, for extra exports
        Args:
            transform: MObject or Pymel.core.nodetypes.Transform
        """
        if isinstance(transform, pm.nodetypes.Transform):
            transform = OpenMaya.MSelectionList().add(str(transform)).getDependNode(0)

        transform_fn = OpenMaya.MFnTransform(transform)
        if not transform_fn.hasAttribute(self.attrCompoundName):
            logger.info('%s does not has attribute: %s' % (transform_fn.fullPathName(), self.attrCompoundName))
            return

        # get compound attr using api
        compoudAttr = transform_fn.attribute(self.attrCompoundName)
        compoudAttr_fn = OpenMaya.MFnCompoundAttribute(compoudAttr)
        logger.debug('addExtraPathAttr: CompoundAttr: %s' % compoudAttr_fn.name)
        compoudAttr_childs = compoudAttr_fn.numChildren()

        # create new string attribute to store new path
        stringData = OpenMaya.MFnStringData().create(path)  # mobject string data with path
        fAttr = OpenMaya.MFnTypedAttribute()
        pathAttr = fAttr.create('%s%s' % (self.attrPathName, compoudAttr_childs), 'pt%s' % compoudAttr_childs, OpenMaya.MFnData.kString, stringData)
        fAttr.keyable = True
        fAttr.storable = True
        fAttr.readable = True
        fAttr.writable = True
        # add attribute
        transform_fn.addAttribute(pathAttr)
        logger.debug('addExtraPathAttr: Attr created: %s%s' % (self.attrPathName, compoudAttr_childs))

        # add new path attribute under compoundAttr
        compoudAttr_fn.addChild(pathAttr)
        logger.debug('addExtraPathAttr: Set as child of %s: %s' % (compoudAttr_fn.name, fAttr.name))

    def removeExtraPath(self, transform, index):
        """
        Removes an attribute inside the compound attribute.
        Removes the index attr and the rest of attributes, then recreate the rest of attributes.
        Args:
            transform: Pymel.core.nodetypes.Transform
            index: index of attr to delete inside the compound attr
        """
        assert isinstance(transform, pm.nodetypes.Transform), 'Transform arg must be a Pymel.core.nodetypes.Transform'

        # store path attributes
        paths = transform.attr(self.attrCompoundName).get()

        # get mDagPath
        mSellist = OpenMaya.MSelectionList().add(str(transform))
        mDagPath = mSellist.getDagPath(0)
        # access to compound attribute, we need to delete desired paths
        mFnTransform = OpenMaya.MFnTransform(mDagPath)
        compoundAttr = mFnTransform.attribute(self.attrCompoundName)
        mfnCompoundAttr = OpenMaya.MFnCompoundAttribute(compoundAttr)

        for i in range(index, len(paths)):
            try:
                # delete path attribute inside compound attribute
                child = mfnCompoundAttr.child(index)  # MObject attribute
                mFnTransform.removeAttribute(child)  # use OpenMaya.MFnTransform to delete the attribute

            except:
                logger.warn('can not delete attr: %s.%s%s' % (transform, self.attrPathName, index))

        # once we have deleted all attributes, we recreate the rest of attributes
        for i in range(index, len(paths)):
            if i != index:
                self.addExtraPathAttr(transform, paths[i])


    def removeAttr(self, *items):
        """
        this method search the attributes on the demanded items.
        If not items are argued, remove attr from selection
        Is necessary use constructList after this method for refresh the items list
        Args:
            items: (str, pynode, ...) or nothing
        """
        # if nothing in arg items, create items list from selection
        if not len(items):
            items = pm.ls(sl=True, type='transform')

        for item in items:
            # check if item is pynode
            if not isinstance(item, pm.nodetypes.Transform):
                logger.debug('Create Pynode from: %s, %s' % (item, type(item)))
                item = pm.PyNode(item)

            # deleteAttrs
            try:
                item.attr(self.attrCompoundName).delete()
                logger.info('Remove attribute: %s.%s' % (item, self.attrCompoundName))

            except:
                logger.warn('Can not delete attr: %s' % self.attrCompoundName)

                # if compound attributes can not be removed, check if bool and path attributes exist and delete
                for attr in (self.attrBoolName, self.attrPathName):
                    try:
                        item.attr(attr).delete()
                        logger.info('Remove attribute: %s.%s' % (item, attr))

                    except:
                        logger.warn('Can not delete attr: %s' % attr)

    def export(self, visible):
        """
        Export elements in the list with the bool attr True
        Args:
            visible: (Bool) If True, only export objects with visibility True

        """
        for item in self:
            # check values
            if (item.visibility.get() or not visible) and item.attr(self.attrBoolName).get():
                # get compound children
                compoundAttributes = item.attr(self.attrCompoundName).get()[1:]
                for path in compoundAttributes:
                    # check if path exist if not, jump next item
                    if not os.path.exists(path):
                        logging.warn('Does not exist path: %s, %s' % (path, item))
                        continue

                    path = os.path.join(path, str(item)+'.fbx')
                    path = os.path.normpath(path)
                    logger.debug('path: %s' % path)

                    # select the exportable element, we use the flag -s in FBXExport to export selection
                    pm.select(item, r=True)
                    # Explanation to use FBXExport, we have to use pm.mel.eval pm.FBXExport is bugged
                    pm.mel.eval('FBXExport -f "%s" -s;' % path.replace('\\', '/'))  # we replace \ for /, if not maya give us an error

                    logging.info('%s exported to: %s' % (item, path))

        pm.select(cl=True)

    export.__doc__ = """
                         Docstring For each item in the class list, export it to attrPathName path.
                         Only if attr {0} is True and visibility is True too.""".format(attrBoolName)

    def __hash__(self):
        # review: do not understand this
        return hash(len(self))

"""
to use:
from FbxExporter import FbxExporter
reload(FbxExporter)
fbxExp = FbxExporter.FbxExporter.instance()
"""