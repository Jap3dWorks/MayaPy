"""
TODO: UI for FbxExporter
    We need:
        A widget with exportable objects:
            Here we can change exp attr or path attr. preferable with right click.
        Refresh.
        Export button.
        AddObj button.
            On clicked: PathExplorer window.
                        Add attributes.

"""
from PySide2 import QtCore, QtGui, QtWidgets
from shiboken2 import wrapInstance
from maya import OpenMayaUI as omui
import pymel.core as pm

import logging
logging.basicConfig()
logger = logging.getLogger('Fbx Exporter UI:')
logger.setLevel(logging.INFO)