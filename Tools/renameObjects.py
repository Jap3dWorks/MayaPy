import pymel.core as pm

def renameObjects(objects=None, name='name', zone=None,  side=None, identifier=None):
    """
    rename with name convention
    Args:
        objects: list or tuple PyNode objects
        name: name of object
        zone: zone were object is
        identifier: extra identifier info
        side: 'left' or 'right', if this arg is not specified it will be auto with z axis in front
    """

    selection = objects if objects else pm.ls(sl=True, dag=True)
    print('object list: %s' % selection)
    # TODO: diferent side, diferent numeration, with a dictionary?
    # p.e: numLoc ={pm.nodetype:[type,{'left':1, 'right':1, None:1}]    } -> numLoc[side] += 1
    typesObject = {}

    for i in ('locator', 'aimConstraint', 'pointConstraint', 'mesh', 'ikHandle', 'ctr'):
        sideDictionaty = {}
        for n in ('left', 'right', None):
            sideDictionaty[n] = 1
        typesObject[i] = sideDictionaty
    
    for i in selection:
        rename = name
        typeNode = None
        num = None

        # if no side, auto side
        # nurbs
        if not side:
            try:
                translation = i.getTranslation(space='world')
            except:
                translation = i.getTransform().getTranslation(space='world')

            print('%s translation: %s' % (str(i), translation))
            sideTemp = 'left' if translation[0] > 0 else 'right' if translation[0] < 0 else None
            # x = 0, no side identifier

        else:
            sideTemp = side

        if isinstance(i, pm.nodetypes.Locator):
            typeNode = 'locator'
            num = typesObject[typeNode][sideTemp]
            typesObject[typeNode][sideTemp] += 1
        elif isinstance(i, pm.nodetypes.AimConstraint):
            typeNode = 'aimConstraint'
            num = typesObject[typeNode][sideTemp]
            typesObject[typeNode][sideTemp] += 1
        elif isinstance(i, pm.nodetypes.PointConstraint):
            typeNode = 'pointConstraint'
            num = typesObject[typeNode][sideTemp]
            typesObject[typeNode][sideTemp] += 1
        elif isinstance(i, pm.nodetypes.Mesh):
            typeNode = 'mesh'
            num = typesObject[typeNode][sideTemp]
            typesObject[typeNode][sideTemp] += 1
        elif isinstance(i, pm.nodetypes.IkHandle):
            typeNode = 'ikHandle'
            num = typesObject[typeNode][sideTemp]
            typesObject[typeNode][sideTemp] += 1
        elif isinstance(i, pm.nodetypes.NurbsCurve):
            typeNode = 'ctr'
            num = typesObject[typeNode][sideTemp]
            typesObject[typeNode][sideTemp] += 1
        else:
            # if is transform and do not has shape, it is a grp
            if isinstance(i, pm.nodetypes.Transform) and not i.getShape():
                typeNode = 'grp'

        for a in (zone, sideTemp, identifier, num, typeNode):
            if a:
                rename += '_%s' % a
        try:
            i = i.getTransform()
        except:
            pass

        i.rename(rename)