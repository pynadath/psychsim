class Action(dict):
    def __init__(self,arg={}):
        dict.__init__(self,arg)
        self._string = None
        

    def __setitem__(self,key,value):
        self._string = None
        dict.__setitem__(self,key,value)

    def __str__(self):
        if self._string is None:
            elements = []
            keys = self.keys()
            for special in ['subject','verb','object']:
                if self.has_key(special):
                    elements.append(self[special])
                    keys.remove(special)
            keys.sort()
            elements += map(lambda k: self[k],keys)
            self._string = '-'.join(elements)
        return self._string

    def __hash__(self):
        return hash(str(self))
    
class ActionSet(set):
    def __init__(self,iterable=[]):
        set.__init__(self,iterable)
        self._string = None

    def __str__(self):
        if self._string is None:
            self._string = ','.join(map(str,self))
        return self._string

    def __hash__(self):
        return hash(str(self))
