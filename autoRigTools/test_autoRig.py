from maya import cmds

from autoRigTools import autoRig

def model_import():
    cmds.file(new=True, force=True)
    cmds.file('D:/_docs/_Animum/Akona/skinCluster/akona_skin.ma', i=True, force=True)
    # cmds.setAttr('akona_model_grp.visibility', True)


def spine_head_leg_akona():

    reload(autoRig)
    akonaRig = autoRig.autoRig()
    akonaRig.autoSpine()
    akonaRig.autoNeckHead()
    akonaRig.autoLeg('left')
    akonaRig.autoLeg('right')


    # cmds.parentConstraint('akona_IK_spine_chest_1_ctr','akona_clavicle_left_joint1', maintainOffset=True)
    # cmds.parentConstraint('akona_IK_spine_chest_1_ctr','akona_clavicle_right_joint1', maintainOffset=True)