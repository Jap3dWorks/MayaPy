import Tools
import maya.cmds as mc


def uvOrientAndLookUp():
    saveSelection = mc.ls(sl=True, type='float2')
    shells = Tools.UvShellTools.uvShells()
    mc.select(saveSelection, r=True)
    Tools.UvShellTools.stackShells()
    mc.select(clear=True)
    for shell in shells:
        Tools.UvShellTools.uvShellOrient(Shell=shell)
        Tools.UvShellTools.uvShellUp(Shell=shell)


uvOrientAndLookUp()
