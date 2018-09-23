class singleton(object):
    
    _instance=None
    _bool=False
    
    @classmethod
    def instance(cls):
        # if _instance = None, create a class instance
        if cls._instance == None:
            # cls._bool = True
            cls._instance = cls()
            # returns a instance of the class stored in _instance
        else:
            print 'instanced'
        cls._instance._bool = True
        # print 'cls._bool -> %s' % cls._instance._bool
        # print 'singleton._bool -> %s' % singleton._bool
        return cls._instance
            
    def __init__(self):
        super(singleton,self).__init__()
        self.var1 = 5
        self.var2 = 10
        
        print 'bool -> %s' % self._bool
        
        if not self._bool:
            print 'raise'
        
            
            
print'___C____'
c = singleton()
print hex(id(c))
print c._instance

print '____a____'        
a = singleton.instance()
print a._instance
print a._bool
a.var1 = 6
print a.var1
print hex(id(a))

b = singleton.instance()
print b._instance
print b.var1
print hex(id(b))
print a._instance
print hex(id(a))

print'___C____'
c = singleton()
print hex(id(c))
print c._instance
