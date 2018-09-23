import pymel.core as pm

import logging
logging.basicConfig()
logger = logging.getLogger('FbxExporterShelf:')
logger.setLevel(logging.INFO)

def FbxExporterInstall():
    DTag = 'FbxExporter'
    icLab = 'FbxExp'
    ann = 'Click export, Double click UI'
    shelf = 'JAShelf'
    icon = 'fbxReview.png'
    
    command = """
from FbxExporter import FbxExporter
fbxExp = FbxExporter.FbxExporter.instance()
if len(fbxExp):
	fbxExp.export(True)"""

    command2 = """
from FbxExporter import FbxExporterUI
from FbxExporter import FbxExporter
ui = FbxExporterUI.FbxExporterUI(True)"""

    if not pm.layout(shelf, q=True, ex=True):
        pm.mel.addNewShelfTab(shelf)

    shelfButtons = pm.shelfLayout(shelf, q=True, ca=True)
    print shelfButtons
    if isinstance(shelfButtons, list):
        for button in shelfButtons:
            if pm.shelfButton(button, q=True, docTag=True) == DTag:
                logging.warn('%s is yet in your shelf tab' % icLab)
                return

    pm.shelfButton('FbxExp', ann=ann, iol=icLab, i1=icon, dtg=DTag, c=command, dcc=command2, p=shelf)


if __name__ == "__main__":
    FbxExporterInstall()