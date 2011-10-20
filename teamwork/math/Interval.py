import string
from types import *
from xml.dom.minidom import *

class Interval:
    """Interval representation"""
    
    # Minimum value for intervals
    FLOOR = -1.0
    # Maximum value for intervals
    CEILING = 1.0
    # Minimum distance (used for testing equality)
    QUANTUM = 0.0001
    
    def __init__(self,lo=FLOOR,hi=CEILING):
        """Interval constructor...creates an interval [lo,hi]"""
        self.lo = max(min(min(lo,hi),Interval.CEILING),Interval.FLOOR)
        self.hi = max(min(max(lo,hi),Interval.CEILING),Interval.FLOOR)

    def mean(self):
        """Returns the midpoint of this interval"""
        return (self.lo+self.hi)/2.0
    
    def __add__(self,other):
        """Enables I1+I2 and I1+x"""
        if type(other) in [IntType,LongType,FloatType]:
            return Interval(self.lo+float(other),self.hi+float(other))
        else:
            try:
                return Interval(self.lo+other.lo,self.hi+other.hi)
            except AttributeError:
                raise TypeError,'non-interval addend ('+`type(other)`+')'

    def __neg__(self):
        """Enables -I1"""
        return Interval(-self.hi,-self.lo)
    
    def __sub__(self,other):
        """Enables I1-I2 and I1-x"""
        return self + (-other)

    def __mul__(self,other):
        """Enables I1*I2 and I1*x"""
        if type(other) in [IntType,LongType,FloatType]:
            return Interval(self.lo*float(other),self.hi*float(other))
        else:
            try:
                values = []
                values.append(self.lo*other.lo)
                values.append(self.lo*other.hi)
                values.append(self.hi*other.lo)
                values.append(self.hi*other.hi)
                return Interval(min(values),max(values))
            except AttributeError:
                raise TypeError,'non-interval multiplicand ('+`type(other)`+')'

    def __div__(self,other):
        """Enables I1/I2 and I1/x"""
        if type(other) in [IntType,LongType,FloatType]:
            return Interval(self.lo/float(other),self.hi/float(other))
        else:
            try:
                values = []
                values.append(self.lo/other.lo)
                values.append(self.lo/other.hi)
                values.append(self.hi/other.lo)
                values.append(self.hi/other.hi)
                return Interval(min(values),max(values))
            except AttributeError:
                raise TypeError,'non-interval divisor ('+`type(other)`+')'
        
    def __lt__(self,other):
        """Enables I1<I2 and I1<x"""
        if type(other) in [IntType,LongType,FloatType]:
            return self.hi <= float(other)-Interval.QUANTUM
        else:
            try:
                return self.hi <= other.lo-Interval.QUANTUM
            except AttributeError:
                raise TypeError,'non-interval comparison ('+`type(other)`+')'

    def __gt__(self,other):
        """Enables I1>I2 and I1>x"""
        if type(other) in [IntType,LongType,FloatType]:
            return self.lo >= float(other)+Interval.QUANTUM
        else:
            try:
                return self.lo >= other.hi+Interval.QUANTUM
            except AttributeError:
                raise TypeError,'non-interval comparison ('+`type(other)`+')'

    def __eq__(self,other):
        """Enables I1==I2 and I1==x"""
        if type(other) in [IntType,LongType,FloatType]:
            return abs(self.lo-float(other))<Interval.QUANTUM and \
                   abs(self.hi-float(other))<Interval.QUANTUM
        else:
            try:
                return abs(self.lo-other.lo)<Interval.QUANTUM and \
                       abs(self.hi-other.hi)<Interval.QUANTUM
            except AttributeError:
                raise TypeError,'non-interval comparison ('+`type(other)`+')'

    def __ne__(self,other):
        """Enables I1!=I2 and I1!=x"""
        return not (self == other)
    
    def __le__(self,other):
        """Enables I1<=I2 and I1<=x"""
        return self < other or self == other

    def __ge__(self,other):
        """Enables I1>=I2 and I1>=x"""
        return self > other or self == other

    def __contains__(self,other):
        """Enables I2 in I1 and x in I1"""
        if type(other) in [IntType,LongType,FloatType]:
            return float(other) >= self.lo and float(other) <= self.hi
        else:
            try:
                return other.lo >= self.lo and other.hi <= self.hi
            except AttributeError:
                raise TypeError,'non-interval comparison ('+`type(other)`+')'

    def __abs__(self):
        """Enables abs(I1)"""
        if self.lo > 0.0:
            return self
        elif self.hi < 0.0:
            return Interval(-self.hi,-self.lo)
        else:
            return Interval(0.0,max(-self.lo,self.hi))
        
    def __repr__(self):
        return '[%6.4f,%6.4f]' % (self.lo,self.hi)

    def __getitem__(self,index):
        """Allows indexing to get the bounds of this interval

        I['lo'] or I[0] returns the low bound of I; I['hi'] or I[1]
        returns its high bound"""
        if index == 'lo' or index == 0:
            return self.lo
        elif index == 'hi' or index == 1:
            return self.hi
        else:
            raise IndexError

    def __setitem__(self,index,value):
        """Allows indexing to set the bounds of this interval

        I['lo']= or I[0]= sets the low bound of I; I['hi']= or I[1]=
        sets its high bound"""        
        if index == 'lo' or index == 0:
            self.lo = floor(value)
        elif index == 'hi' or index == 1:
            self.hi = ceil(value)
        else:
            raise IndexError

    def __float__(self):
        return self.mean()

    def __xml__(self):
        doc = Document()
        root = doc.createElement('interval')
        doc.appendChild(root)
        node = doc.createElement('lo')
        node.appendChild(doc.createTextNode(`self.lo`))
        root.appendChild(node)
        node = doc.createElement('hi')
        node.appendChild(doc.createTextNode(`self.hi`))
        root.appendChild(node)
        return doc

    def parse(self,node):
        child = node.firstChild.firstChild
        while child:
            self[child.tagName] = float(child.firstChild.data)
            child = child.nextSibling

    def isPoint(self):
        """Returns true iff the interval is a point interval"""
        return self.width() < self.QUANTUM

    def width(self):
        """Returns the float width of this interval"""
        return self.hi - self.lo
    
def floor(value):
    """Returns the maximum between the given value and the interval floor"""
    return max(value,Interval.FLOOR)

def ceil(value):
    """Returns the minimum between the given value and the interval ceiling"""
    return min(value,Interval.CEILING)

def str2Interval(content):
    values = string.split(content[1:-1],',')
    if len(values) != 2:
        raise TypeError,'Illegal string format for Interval: %s' % content
    return Interval(float(values[0]),float(values[1]))
    
if __name__ == '__main__':
    import os.path
    

    x = Interval(0.1,0.4)
    y = Interval(0.3,0.6)
    print 0.7 in y

    x[0] = 0.3
    x['hi'] = 0.5
    print x
    i = str2Interval('[0.,1.]')
    print i.lo
    print i.hi
    name = '/tmp/%s.xml' % (os.path.basename(__file__))
    file = open(name,'w')
    file.write(i.__xml__().toxml())
    file.close()

    i = Interval()
    i.parse(parse(name))
    print i
    
