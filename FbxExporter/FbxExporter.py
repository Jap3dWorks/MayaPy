# fbx Exporter.
"""
 TODO the idea is add two attributes:
    exp -> boolean // indicate if is exportable
    path -> string // path where objects will be export

    will export object and children. transform nodes only
    script will search items with exp attr and path attr and construct a dictionary with them.
    {self.object: [exp, path], self.object2: [exp, path], ...}

"""
import pymel.core as pm

import logging
logging.basicConfig()
logger = logging.getLogger('Fbx Exporter:')
logger.setLevel(logging.INFO)

class FbxExporter(dict):
    def __init__(self):
        super(FbxExporter, self).__init__()

    def constructDictionary(self):
        # search items
        items = pm.ls(tr=True)


    def addAttributes(self):
        pass

    def export(self):
        pass