# introduce part name don't pair. create list of lists with pairs
from maya import cmds

import pymel.core as pm
import re

import logging
logging.basicConfig()
logger = logging.getLogger('nameMatcher:')
logger.setLevel(logging.DEBUG)

# TODO: match from list, match from scene

class nameMatcher(list):
    def __init__(self):
        super(nameMatcher, self).__init__()
        self.initialSet = []

    def MatchFromSelection(self, *args):
        """
        I don't remember how this works
        find object with the same name except the *args string
        isn't exclusive, it should be i think
        Args:
            *args:
        """
        # TODO: exclusive
        # no pymel, because pymel return class nodes, we need simple strings
        self.initialSet = set(cmds.ls(sl=True))
        assert len(self.initialSet) >= 2, 'Select at least two elments'

        while len(self.initialSet):
            firstElement = self.initialSet.pop()
            # store match elements in matchElements
            matchElements = []

            # iterate for key word
            for arg in args:
                # check if key word is in first pop element

                if arg in firstElement:
                    matchElements.append(firstElement)
                    # prepare new set without first arg
                    restArgs = set(args)
                    restArgs.remove(arg)

                    # iterate again with rest of key words to find match elements
                    for restArg in restArgs:
                        searchElements = firstElement.replace(arg, restArg)
                        try:
                            # if remove do not find element, give us an error
                            self.initialSet.remove(searchElements)
                            matchElements.append(searchElements)
                        except:
                            logger.debug('%s not found' % searchElements)
                            pass

                    # avoid unnecessary iterations
                    break

                logger.debug('%s not found in %s' % (arg, firstElement))
            if len(matchElements):
                self.append(matchElements)


def renameObjects(name='name', objectType=None, zone=None, side=None, objects=None):
    """
    rename with name convention:
    name_objectType_zone_side_n_functionality
    p.e: platform_stick_floor01_left_2_locator
    p.e: akona_chest_spine_IK_1_ctr
    p.e: akona_foreArm_arm_left_twist_1_jnt

    Args:
        objects: list or tuple PyNode objects
        name: name of object
        zone: zone were object is
        objectType: extra info about this object functions
        side: 'left' or 'right', if this arg is not specified it will be auto with z axis in front
    """
    selection = objects if objects else pm.ls(sl=True)
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

    # fill typesObject dict
    for i in range(0, len(pynodeTypes), 2):
        sideDic = {}
        pynodeType = [pynodeTypes[i + 1]]
        for n in ('left', 'right', None):
            sideDic[n] = 1

        pynodeType.append(sideDic)
        typesObject[pynodeTypes[i]] = pynodeType
    logger.debug('selection: %s' % selection)
    for i in selection:
        rename = name
        typeNode = None
        num = None

        # if no side, auto side
        try:
            # if get error, we had selected a shape,
            # so we jump to the next iteration
            translation = i.getTranslation(space='world')
        except:
            continue

        if not side:
            # x = 0, no side identifier
            sideTemp = 'left' if translation[0] > 0 else 'right' if translation[0] < 0 else None
        else:
            sideTemp = side

        try:
            if i.getShape():
                i = i.getShape()
        except:
            pass

        if type(i) in typesObject:
            typeNode = typesObject[type(i)][0]
            num = typesObject[type(i)][1][sideTemp]
            typesObject[type(i)][1][sideTemp] += 1

        else:
            continue

        for a in (objectType, zone, sideTemp, num, typeNode):
            if a:
                rename += '_%s' % a

        # if node has transform, we should rename the transform node
        try:
            i = i.getTransform()
        except:
            pass

        i.rename(rename)