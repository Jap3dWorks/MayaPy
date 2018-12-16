from maya import cmds
import re

from autoRigTools import autoRig
#"D:/_docs/_Animum/Akona/skinCluster/proceso/akona_skin05.ma"
#'D:/_docs/_Animum/Akona/skinCluster/akona_skin.ma'
def model_import():
    cmds.file(new=True, force=True)
    cmds.file('D:/_docs/_Animum/Akona/skinCluster/akona_skinPSD.ma', i=True, force=True)
    # cmds.setAttr('akona_model_grp.visibility', True)


def spine_head_leg_akona(name='akona'):

    reload(autoRig)
    akonaRig = autoRig.RigAuto(chName=name, path='D:\_docs\_Animum\Akona')
    akonaRig.spine_auto()
    akonaRig.neckHead_auto()

    # legs
    akonaRig.ikFkChain_auto('left', akonaRig.ikControllers['spine'][0], 'leg', True, lambda: akonaRig.foot_auto('left', ('leg', 'foot', 'toe'), 'zx'))
    akonaRig.ikFkChain_auto('right', akonaRig.ikControllers['spine'][0], 'leg', True, lambda: akonaRig.foot_auto('right', ('leg', 'foot', 'toe'), 'zx'))
    #akonaRig.arm_auto('left')

    # arms
    akonaRig.ikFkChain_auto('left', akonaRig.ikControllers['spine'][-1], 'arm', True, lambda: akonaRig.hand_auto('left', ('arm', 'hand', 'finger'), None), lambda: akonaRig.clavicle_auto('left', 'clavicle'))
    akonaRig.ikFkChain_auto('right', akonaRig.ikControllers['spine'][-1], 'arm', True, lambda: akonaRig.hand_auto('right', ('arm', 'hand', 'finger'), None), lambda: akonaRig.clavicle_auto('right', 'clavicle'))

    #____#
    #cmds.parentConstraint('akona_ik_spine_chest_1_ctr', 'akona_clavicle_left_joint', maintainOffset=True)
    #qcmds.parentConstraint('akona_ik_spine_chest_1_ctr', 'akona_clavicle_right_joint', maintainOffset=True)