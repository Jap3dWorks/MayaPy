import maya.api.OpenMaya as OpenMaya
import pymel.core as pm

def findAttr(attr, *args):
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
            transform_attrName = transform_mfn.findPlug(transform_mfn.attribute(i), True).info
            if transform_attrName == '%s.%s' % (transform, attr):
                # print 'attr Found: %s -> %s ' % (transform_attrName, transform)
                transformReturn.append(pm.PyNode(transform))
        
        mselList_It.next()
    
    return transformReturn
    
    
def listAttrTypes():
    mSelList = OpenMaya.MGlobal.getActiveSelectionList()
    
    mSelIt = OpenMaya.MItSelectionList(mSelList, OpenMaya.MFn.kTransform)
    
    while not mSelIt.isDone():
        transform =  mSelIt.getDagPath()
        mfnTransform = OpenMaya.MFnTransform(transform)
        
        for i in range(mfnTransform.attributeCount()):
            transformAttr = mfnTransform.attribute(i)
            transformAttr_plug = mfnTransform.findPlug(transformAttr, True)
            print ('%s is type: %s' % (transformAttr_plug.info, transformAttr.apiTypeStr))
            
        mSelIt.next()
    
    



if __name__=='__main__':
    findAttr('exp', 'pCube56')
    # listAttrTypes()