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
    print ('this is shit')
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