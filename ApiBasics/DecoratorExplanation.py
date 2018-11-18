def foo():
    print('This is foo')

print('\n\n------------------------\nCalling foo without wrapper')
foo()

print(foo.__name__)

def spam(func):
    print('this is spam')
    value = func()
    print ('spam is done')
    return value

print('\n\n------------------------\nCalling foo directly wrapped by spam')

spam(foo)



def deferSpam(func):
    def wrapperSpam(*args, **kwargs):
        print ('this is wrapper spam spam')
        value = func(*args, **kwargs)
        print('wrapperSpam is done')
        return value
    return wrapperSpam

print('\n\n--------------------\nCalling foo wrapped by wrapperSpam created by deferSpam\n')
foo = deferSpam(foo)

foo()

print ('\n\n ----------------------\n')
print(foo.__name__)

@deferSpam
def hello(name):
    print('hello %s' % name)

print ('\n\n------------------\n')
hello('david')

print (hello.__name__)

print ('\n\n------------------\n')
from functools import wraps

def eggs(func):
    @wraps(func)
    def wrapper(*arg, **kwargs):
        print('this is eggs')
        ret = func(*arg, **kwargs)
        print ('eggs is done')
        return  ret
    return wrapper

def eggsShit(func):
    print ('this is egg shit')
    @wraps(func)  # decorator factory
    def wrapper(*args, **kwargs):  # create tuple and dictionaries from values
        print ('this is wrapper')
        print (type(args), type(kwargs))
        ret = func(*args, **kwargs)  # decompose the tuple and dictionaries into values0, values1, ...
        print ('eggsShit is done')
        return ret
    return wrapper


@eggsShit
def goodbye(name = 'mary'):
    print('Goodbye, %s' %name)


goodbye()

# print(goodbye.__name__)

#######################
#DECORATORS IN A CLASS#
#######################
from maya import cmds
import time
class cubeCreator(object):
    # decorator class
    # other examples in autoRig
    class decoratorClass(object):
        def __init__(self, key):
            self.key = key

        def __call__(self, func):
            def inner(*args, **kwargs):
                print ('hello from', self.key)

                check = None

                if 'left' in args or 'right' in args:
                    check = 'left'

                if 'side' in kwargs:
                    check = True

                print ('check %s' % check)

                timeTrack = time.time()
                result = func(*args, **kwargs)

                print ('time: %s' % (time.time() - timeTrack))
                return result

            return inner

    def __init__(self, x, y, z):
        super(cubeCreator, self).__init__()

        self.x = x
        self.y = y
        self.z = z

    @decoratorClass('keyArg')
    def create_cube(self, name, side, world='earth'):
        cmds.polyCube(h=self.x, d=self.y, w=self.z, name=name + side)

    @decoratorClass('sphere')
    def create_sphere(self, name, world='earth'):
        cmds.polySphere(r=self.x, name=name)


cubecreatorvar = cubeCreator(10, 10, 10)
cubecreatorvar.create_cube('francesca', side='right', world='earth')
cubecreatorvar.create_sphere('manoly')