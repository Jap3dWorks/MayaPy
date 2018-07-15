from maya.api import OpenMaya as om

# tells maya that we are using de new api
def maya_useNewAPI():
    pass

class HelloWorldCmd(om.MPxCommand):

    # this var are ever necessary
    kPluginCmdName = 'hello'

    # flag names
    kNameFlag = '-n'
    kNameLongFlag = '-name'

    # function that performs the action command
    def doIt(self, args):
        argData = om.MArgDatabase(self.syntax(), args)

        # check if a arg is provided
        if argData.isFlagSet(HelloWorldCmd.kNameFlag):
            name = argData.flagArgumentString(HelloWorldCmd.kNameFlag, 0)

        else:
            name = 'world'

        om.MGlobal.displayInfo("Hello, %s!" % name)

# function that will create our command
def cmdCreator():
    return HelloWorldCmd()

def syntaxCreator():
    syntax = om.MSyntax()

    syntax.addFlag(
        HelloWorldCmd.kNameFlag, HelloWorldCmd.kNameLongFlag, om.MSyntax.kString)
    return syntax


def initializePlugin(plugin):
    pluginFn = om.MFnPlugin(plugin)
    try:
        pluginFn.registerCommand(
            HelloWorldCmd.kPluginCmdName, cmdCreator, syntaxCreator)
    except:
        om.MGlobal.displayError('Failed to register command: %s\n' % HelloWorldCmd.kPluginCmdName)
        raise
# tell maya how to unload plugin
def uninitializePlugin(plugin):
    pluginFn = om.MFnPlugin(plugin)

    try:
        pluginFn.deregisterCommand(HelloWorldCmd.kPluginCmdName)
    except:
        om.MGlobal.displayError('Failed to deregister command: %s\n' % HelloWorldCmd.kPluginCmdName)
        raise
