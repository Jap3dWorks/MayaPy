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
    # type = OpenMaya.MFn.kNumericAttribute
    typeAttr = OpenMaya.MFnNumericData.kBoolean
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
        self = self.findAttr(self.attrBoolName, self.typeAttr)
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
            mfnStringData = OpenMaya.MFnStringData()
            # mfnStringData.set(path)
            fAttr = OpenMaya.MFnTypedAttribute()
            pathAttr = fAttr.create(self.attrPathName, 'pt', OpenMaya.MFnData.kString, mfnStringData.object())
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

            # iterate attributes of the node
            for i in range(transform_fn.attributeCount()):
                attr_mOb = transform_fn.attribute(i)  # mobject with the attribute
                attr_plug = transform_fn.findPlug(attr_mOb, True).info
                if '%s.%s' % (transform, self.attrBoolName) == attr_plug and attr_mOb.apiType() == self.typeAttr:
                    logger.info('%s already has attribute: %s' % (transform, attr_plug))
                    break
            else:
                # if for no break, is because the loop does not find the desired attribute.
                # so we can add it
                transform_fn.addAttribute(compoundAttr)
                pathAttr_plug = transform_fn.findPlug(self.attrPathName, True)
                logger.debug('%s has atrribute %s: %s' % (transform, pathAttr_plug, transform_fn.hasAttribute(self.attrPathName)))
                try:
                    pathAttr_plug.setString(path)
                except:
                    logger.error('Failed to entry path')
                    raise

            mSelList_It.next()

    def export(self):
        pass

"""
from FbxExporter import FbxExporter
reload(FbxExporter)
fbxExp = FbxExporter.FbxExporter()
"""