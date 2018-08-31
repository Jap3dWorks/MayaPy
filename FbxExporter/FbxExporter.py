# fbx Exporter.
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
import sys
import os

import logging
logging.basicConfig()
logger = logging.getLogger('Fbx Exporter:')
logger.setLevel(logging.DEBUG)

class FbxExporter(list):
    attrBoolName = 'exp'
    attrPathName = 'FbxExpPath'
    typeAttr = OpenMaya.MFnNumericData.kBoolean
    typeAttr_Find = OpenMaya.MFn.kNumericAttribute
    defaultPath = os.getenv('MAYA_APP_DIR')

    def __init__(self):
        super(FbxExporter, self).__init__()

    def constructList(self):
        """
        This method fill the self.list
        Returns:

        """
        # clear previous list
        self[:] = []

        # search items
        self = self.findAttr(self.attrBoolName, self.typeAttr_Find)
        logger.debug('Class list items:%s items found: %s' % (len(self), self))

    def findAttr(self, attr, type, *args):
        """
        Args:
            attr: Attribute desired
            *args: objects we want to check, if no *args check entire scene

        Returns: Pymel objects List that contain the attribute
        """

        mselList = OpenMaya.MSelectionList()
        # if some args are given
        if len(args):
            for i in args:
                mselList.add(i)
        # no args check entire scene
        else:
            mselList.add('*')

        # msellist iterator
        mselList_It = OpenMaya.MItSelectionList(mselList, OpenMaya.MFn.kTransform)

        transformReturn = []

        while not mselList_It.isDone():
            transform = mselList_It.getDagPath()
            transform_mfn = OpenMaya.MFnTransform(transform)

            for i in range(transform_mfn.attributeCount()):
                transform_attr = transform_mfn.attribute(i)  # MObject
                transform_plug = transform_mfn.findPlug(transform_attr, True).info
                # fixme recollect float attributes, int, and boolean. better only boolean
                # fixme use MFnTransform.hasAttribute() to avoid this loop
                if transform_plug == '%s.%s' % (transform, attr) and transform_attr.apiType() == type:
                    transformReturn.append(pm.PyNode(transform))
                    break

            mselList_It.next()

        return transformReturn

    def addAttributes(self, path=defaultPath):
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
            compoundAttr = fAttr.create('FbxExporter', 'fe')
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
                pathAttr_plug = transform_fn.findPlug(self.attrPathName, True)
                logger.debug('%s has added attribute %s: %s' % (transform, pathAttr_plug, transform_fn.hasAttribute(self.attrPathName)))
                try:
                    pathAttr_plug.setString(path)
                except:
                    logger.error('Failed to entry path')
                    raise

            mSelList_It.next()

    def removeAttr(self):
        pass

    def export(self):
        pass

"""
from FbxExporter import FbxExporter
reload(FbxExporter)
fbxExp = FbxExporter.FbxExporter()
"""