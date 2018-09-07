# fbx Exporter V0.5.
"""
http://evgeniyzaitsev.com/2010/07/28/60/
 TODO the idea is add two attributes:
    exp -> boolean // indicate if is exportable
    path -> string // path where objects will be export

    will export object and children. transform nodes only
    script will search items with exp attr and path attr and construct a dictionary with them.
    {self.object: [exp, path], self.object2: [exp, path], ...}

"""
import pymel.core as pm
import maya.api.OpenMaya as OpenMaya
import os

import logging
logging.basicConfig()
logger = logging.getLogger('Fbx Exporter:')
logger.setLevel(logging.DEBUG)

class FbxExporter(list):
    attrBoolName = 'exp'
    attrPathName = 'FbxExpPath'
    attrCompoundName = 'FbxExporter'
    defaultPath = os.getenv('MAYA_APP_DIR')

    def __init__(self):
        super(FbxExporter, self).__init__()

        # Construct list
        self.__constructList()

    def __constructList(self):
        """
        This method fill the self.list

        """
        # clear previous list and all references
        del self[:]

        # search items
        self.extend(self.__findAttr(self.attrBoolName))
        logger.debug('Class list items:%s items found: %s' % (len(self), self))

    def __findAttr(self, attr, *args):
        """
        Args:
            attr: Attribute desired
            *args: objects we want to check, if no *args check entire scene

        Returns: Pymel objects List that have the attribute
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

            # use transform_mfn.hasAttribute() to avoid this loop
            # fixme: actually, this method doesn not look for the attribute type

            if transform_mfn.hasAttribute(attr):
                transformReturn.append(pm.PyNode(transform))

            mselList_It.next()

        return transformReturn

    def addAttributes(self, path=defaultPath):
        """
        This method adds the attributes necessary to use the script.
        At the end, refresh the self list
        Args:
            path: path where export the fbx
        """
        # get active selection
        mSelList = OpenMaya.MGlobal.getActiveSelectionList()
        mSelList_It = OpenMaya.MItSelectionList(mSelList, OpenMaya.MFn.kTransform)

        # iterate and find if items with the attribute, if have not, add.
        while not mSelList_It.isDone():
            transform = mSelList_It.getDagPath()
            transform_fn = OpenMaya.MFnTransform(transform)

            # create attributes
            fAttr = OpenMaya.MFnNumericAttribute()
            boolAttr = fAttr.create(self.attrBoolName, self.attrBoolName, OpenMaya.MFnNumericData.kBoolean, True)  # get an mObject atttr
            fAttr.keyable = True
            fAttr.storable = True
            fAttr.readable = True
            fAttr.writable = True

            # string path
            fAttr = OpenMaya.MFnTypedAttribute()
            pathAttr = fAttr.create(self.attrPathName, 'pt', OpenMaya.MFnData.kString)
            fAttr.keyable = True
            fAttr.storable = True
            fAttr.readable = True
            fAttr.writable = True

            # compoundAttr
            fAttr = OpenMaya.MFnCompoundAttribute()
            compoundAttr = fAttr.create(self.attrCompoundName, 'fe')
            fAttr.addChild(boolAttr)
            fAttr.addChild(pathAttr)
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
                # Explanation: findPlug very useful to manipulate attr. this method returns a mplug from the name of the attr
                pathAttr_plug = transform_fn.findPlug(self.attrPathName, True)
                logger.debug('%s has added attribute %s: %s' % (transform, pathAttr_plug, transform_fn.hasAttribute(self.attrPathName)))
                try:
                    pathAttr_plug.setString(path)
                except:
                    logger.error('Failed to entry path')
                    raise

            mSelList_It.next()
        self.__constructList()

    def removeAttr(self, *items):
        """
        this method search the attributes on the denamded items.
        If not items are argued, remove attr from selection
        At the end, refresh the self list
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

        self.__constructList()

    def export(self):
        """
        For each item in the class list, export it to attrPathName path.
        Only if attr exp is True and visibility is True too.
        """
        for item in self:
            # check values
            if item.visibility and item.attr(self.attrBoolName).get():
                # get path from path attribute
                path = item.attr(self.attrPathName).get()

                # check if path exist if not, jump next item
                if not os.path.exists(path):
                    logging.warn('Does not exist path: %s, %s' % (path, item))
                    continue

                path = os.path.join(path, str(item)+'.fbx')
                path = os.path.normpath(path)

                # select the exportable element, we use the flag -s in FBXExport to export selection
                pm.select(item, r=True)
                # Explanation to use FBXExport, we have to use pm.mel.eval pm.FBXExport is bugged
                pm.mel.eval('FBXExport -f "%s" -s;' % path.replace('\\', '/'))  # we replace \ for /, if not maya give us an error

                logging.info('%s exported to: %s' % (item, path))

        pm.select(cl=True)

"""
from FbxExporter import FbxExporter
reload(FbxExporter)
fbxExp = FbxExporter.FbxExporter()
"""