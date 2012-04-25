class Action(dict):

    def __init__(self,arg={}):
        dict.__init__(self,arg)
        self._string = None

    def __setitem__(self,key,value):
        self._string = None
        dict.__setitem__(self,key,value)

    def __str__(self):
        if self._string is None:
            
            for key,value in self.items():
                if key == 'subject':
                    main.insert(0,value)
                elif key == 'verb':
        return self._string

    def __hash__(self):
        return hash(str(self))
