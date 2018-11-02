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
    # TODO: maybe dag is to dangerous. should be i.getShape() not i.getTransform()
    print selection

    typesObject = {}
    pynodeTypes = (pm.nodetypes.Locator, 'locator',
                   pm.nodetypes.AimConstraint, 'aimConstraint',
                   pm.nodetypes.PointConstraint, 'pointConstraint',
                   pm.nodetypes.Mesh, 'mesh',
                   pm.nodetypes.IkHandle, 'ikHandle',
                   pm.nodetypes.NurbsCurve, 'ctr',
                   pm.nodetypes.Transform, 'grp',
                   pm.nodetypes.ParentConstraint, 'parentConstraint',
                   pm.nodetypes.Joint, 'jnt')

    for i in range(0, len(pynodeTypes), 2):
        sideDic = {}
        pynodeType = [pynodeTypes[i+1]]
        for n in ('left', 'right', None):
            sideDic[n] = 1

        pynodeType.append(sideDic)
        typesObject[pynodeTypes[i]] = pynodeType

    for i in selection:
        rename = name
        typeNode = None
        num = None

        # if no side, auto side
        if not side:
            try:
                translation = i.getTranslation(space='world')
            except:
                translation = i.getTransform().getTranslation(space='world')

            # x = 0, no side identifier
            sideTemp = 'left' if translation[0] > 0 else 'right' if translation[0] < 0 else None

        else:
            sideTemp = side

        if type(i) in typesObject:
            if isinstance(i, pm.nodetypes.Transform) and i.getShape():
                continue

            typeNode = typesObject[type(i)][0]
            num = typesObject[type(i)][1][sideTemp]
            print('pre plus num %s: %s' % (typesObject[type(i)][0], typesObject[type(i)][1][sideTemp]))
            typesObject[type(i)][1][sideTemp] += 1
            print('post plus num: %s' % typesObject[type(i)][1][sideTemp])

        else:
            continue

        for a in (zone, sideTemp, identifier, num, typeNode):
            if a:
                rename += '_%s' % a

        # if node has transform, we should rename the transform node
        try:
            i = i.getTransform()
        except:
            pass

        i.rename(rename)

    print typesObject