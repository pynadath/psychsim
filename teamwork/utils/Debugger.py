import copy
import string
import sys
import time

class Debugger:
    """Generic debugger class
    @ivar level: attribute, representing debug level (higher means more messages)
    """
    def __init__(self,level=0):
        self.level = level

    def message(self,level=1,str=''):
        """Sends debug messages to the appropriate medium.  Override
        the L{display} method to use different medium
        """
        if level > 10 - self.level:
            self.display(str)

    def display(self,str):
        """Output method.  If not overridden, uses standard output"""
        print str
        sys.stdout.flush()

    def __add__(self,delta):
        debug = copy.copy(self)
        debug.level = debug.level + delta
        if debug.level < 0:
            debug.level = 0
        return debug

    def __sub__(self,delta):
        return self + (-delta)

    def __cmp__(self,other):
        if isinstance(other,Debugger):
            return self.level.__cmp__(other.level)
        else:
            return self.level.__cmp__(other)

    def __repr__(self):
        return 'Debugger ('+`self.level`+')'

    def __copy__(self):
        return self.__class__(self.level)
    
class AccumulateDebugger(Debugger):
    def __init__(self,level=0):
        Debugger.__init__(self,level)
        self.reset()

    def display(self,str):
        self.results.append(str)
##        Debugger.display(self,str)

    def reset(self):
        self.results = []
        
    def __repr__(self):
        self.reset
        return string.join(self.results,'\n')

    def __copy__(self):
        debug = self.__class__(self.level)
        debug.results = self.results
        return debug

class TimedDebugger(AccumulateDebugger):
    def __init__(self,level=0):
        AccumulateDebugger.__init__(self,level)

    def display(self,str):
        newTime = time.time()
        diff = int((newTime-self.lastTime)*1000.0)
        if diff > 0:
            newStr = str + ' ('+`diff`+' ms)'
        else:
            newStr = str
        self.lastTime = time.time()
        AccumulateDebugger.display(self,newStr)

    def reset(self):
        AccumulateDebugger.reset(self)
        self.lastTime = time.time()

    def __copy__(self):
        debug = self.__class__(self.level)
        debug.results = self.results
        debug.lastTime = self.lastTime
        return debug

def quickProfile(cmd,args):
    import hotshot,hotshot.stats
    filename = '/tmp/stats'
    prof = hotshot.Profile(filename)
    prof.start()
    apply(cmd,args)
    prof.stop()
    prof.close()
    stats = hotshot.stats.load(filename)
    stats.strip_dirs()
    stats.sort_stats('time', 'calls')
    stats.print_stats()
    
