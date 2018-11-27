from maya import cmds
import re

from autoRigTools import autoRig

def model_import():
    cmds.file(new=True, force=True)
    cmds.file('D:/_docs/_Animum/Akona/skinCluster/akona_skin.ma', i=True, force=True)
    # cmds.setAttr('akona_model_grp.visibility', True)


def spine_head_leg_akona(name='akona'):

    reload(autoRig)
    akonaRig = autoRig.RigAuto(chName=name, path='D:\_docs\_Animum\Akona')
    akonaRig.spine_auto()
    akonaRig.neckHead_auto()
    akonaRig.leg_auto('left', True)
    akonaRig.leg_auto('right', True)
    #akonaRig.arm_auto('left')

    cmds.parentConstraint('akona_ik_spine_chest_1_ctr', 'akona_clavicle_left_joint', maintainOffset=True)
    cmds.parentConstraint('akona_ik_spine_chest_1_ctr', 'akona_clavicle_right_joint', maintainOffset=True)

    return
    # test twistJoints
    selection = [i for i in cmds.ls() if re.match('^%s_twist._.*_.*_.*_joint$' % name, i)]
    for sel in selection:
        cube = cmds.polyCube(w=2, h=10, d=10)[0]
        cmds.parent(cube, sel)
        cmds.xform(cube, os=True, t=(0,0,0), ro=(0,0,0))